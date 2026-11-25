"""问答工作流。先分类再调用已有服务，不另开 Agent。"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agent.prompts import (
    CHAT_SYSTEM,
    DISCLAIMER,
    PROFILE_UPDATE_SYSTEM,
)
from app.agent.help_guide import HELP_SYSTEM, guide_context
from app.core.llm import generate
from app.rules.engine import evaluate

Route = Literal["knowledge", "recommend", "report", "profile_update", "help", "blocked"]
FoodLister = Callable[[], list["FoodRecord"]]
GraphLookup = Callable[[str], tuple[str, list[dict[str, object]]]]
Retriever = Callable[[str], tuple[str, list[dict[str, object]]]]
ProfileLoader = Callable[[int], dict[str, object]]
Recommender = Callable[[int, str | None, bool], dict[str, object]]
ReportLoader = Callable[[int, str], dict[str, object]]
ReportExplainer = Callable[[int, str], dict[str, object]]

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_ALLERGY = re.compile(r"对([^，。,、]+?)过敏")
_DISLIKE = re.compile(r"(?:不吃|忌口|不喜欢)([^，。,、]+)")
_RELATION = {
    "RECOMMEND": "推荐",
    "AVOID": "避免",
    "LIMIT": "限量",
    "CONTAINS": "含有",
    "COOKED_BY": "做法",
    "AVOID_METHOD": "避免做法",
    "SUBSTITUTE": "可替换",
}

_HELP_MARKERS = (
    "怎么操作", "怎么使用", "如何使用", "怎么用", "如何用", "怎么添加", "如何添加",
    "怎么设置", "如何设置", "怎么查看", "如何查看", "怎么录入", "如何录入", "怎么填写",
    "如何填写", "怎么生成", "如何生成", "怎么转发", "如何转发", "操作步骤", "使用方法",
    "怎么找到", "如何找到", "在哪里", "在哪里看", "怎么打开", "如何打开", "网页怎么",
    "这个怎么", "功能介绍", "有哪些功能", "功能有哪些",
)


@dataclass(frozen=True)
class FoodRecord:
    food_id: int
    name: str
    aliases: tuple[str, ...]
    gi: Decimal | None
    gi_source: str
    kcal: Decimal | None
    carb_g: Decimal | None


@dataclass
class ChatDeps:
    load_profile: ProfileLoader
    list_foods: FoodLister
    graph_links: GraphLookup
    retrieve: Retriever
    recommend: Recommender
    load_report: ReportLoader
    explain_report: ReportExplainer
    food_catalog: tuple[str, ...] = ()


class ChatState(TypedDict, total=False):
    user_id: int
    question: str
    route: Route
    blocked: bool
    block_message: str | None
    profile: dict[str, object]
    facts: list[dict[str, object]]
    relations: list[dict[str, object]]
    chunks: list[dict[str, object]]
    graph_status: str
    rag_status: str
    recommend: dict[str, object]
    report: dict[str, object]
    explain: dict[str, object]
    draft: dict[str, object]
    answer: str
    citation_ids: list[str]
    sources: list[dict[str, object]]


def classify(question: str) -> Route:
    text = question.strip()
    if any(marker in text for marker in _HELP_MARKERS):
        return "help"
    if any(marker in text for marker in ("过敏", "不吃", "忌口", "不喜欢")):
        return "profile_update"
    if any(marker in text for marker in ("做什么", "推荐", "换一批", "来一道", "有什么菜")):
        return "recommend"
    if "冰箱" in text and any(marker in text for marker in ("晚", "午", "早", "做")):
        return "recommend"
    if any(marker in text for marker in ("吃多了", "周报", "日报", "这周我", "今天的热量", "我的热量")):
        return "report"
    if "碳水" in text and any(marker in text for marker in ("这周", "今天", "报告")):
        return "report"
    return "knowledge"


def extract_draft(question: str) -> dict[str, list[str]]:
    allergies = [_split(match.group(1)) for match in _ALLERGY.finditer(question)]
    dislikes = [_split(match.group(1)) for match in _DISLIKE.finditer(question)]
    return {
        "allergies": _unique(item for group in allergies for item in group),
        "dislikes": _unique(item for group in dislikes for item in group),
    }


def correct_draft(question: str, old_draft: dict[str, object]) -> dict[str, list[str]]:
    """用 LLM 理解用户的纠正或补充，返回新草稿。模型不可用时退回正则抽取。"""
    payload = {"old": old_draft or {}, "message": question}
    try:
        raw = generate(
            [
                {"role": "system", "content": PROFILE_UPDATE_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            purpose="chat",
        )
        parsed = _parse_json(raw)
        if parsed is not None:
            allergies = parsed.get("allergies")
            dislikes = parsed.get("dislikes")
            if isinstance(allergies, list) and isinstance(dislikes, list):
                return {
                    "allergies": _unique(allergies),
                    "dislikes": _unique(dislikes),
                }
    except Exception:  # noqa: BLE001
        pass
    return extract_draft(question)


def meal_from_question(question: str) -> str | None:
    if "早" in question:
        return "早餐"
    if "午" in question:
        return "午餐"
    if "晚" in question:
        return "晚餐"
    if "加餐" in question:
        return "加餐"
    return None


def run_chat(deps: ChatDeps, *, user_id: int, question: str) -> dict[str, object]:
    compiled = _compile(deps)
    final = compiled.invoke({"user_id": user_id, "question": question.strip(), "blocked": False})
    return {
        "route": final.get("route") or "knowledge",
        "blocked": bool(final.get("blocked")),
        "block_message": final.get("block_message"),
        "answer": str(final.get("answer") or ""),
        "citation_ids": list(final.get("citation_ids") or []),
        "sources": list(final.get("sources") or []),
        "graph": final.get("graph_status") or "up",
        "rag": final.get("rag_status") or "up",
        "draft": final.get("draft") or {},
        "recommend": final.get("recommend"),
        "report": final.get("report"),
    }


def _compile(deps: ChatDeps) -> Any:
    graph = StateGraph(ChatState)
    graph.add_node("route", lambda state: _route(state, deps))
    graph.add_node("prepare", lambda state: _prepare(state, deps))
    graph.add_node("respond", lambda state: _respond(state, deps))
    graph.set_entry_point("route")
    graph.add_conditional_edges(
        "route",
        lambda state: "stop" if state.get("blocked") else "continue",
        {"stop": "respond", "continue": "prepare"},
    )
    graph.add_edge("prepare", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def _route(state: ChatState, deps: ChatDeps) -> dict[str, object]:
    question = str(state.get("question") or "")
    profile = _safe_profile(deps, int(state["user_id"]))
    diseases = [str(item) for item in profile.get("diseases") or []]
    age = profile.get("age")
    age_value = int(age) if isinstance(age, int) else None
    outcome = evaluate({"diseases": diseases}, age=age_value, user_text=question)
    if outcome.blocked:
        return {
            "route": "blocked",
            "blocked": True,
            "block_message": outcome.block_message,
            "profile": profile,
            "answer": _with_disclaimer(str(outcome.block_message or "请及时就医 / 咨询医生。")),
            "citation_ids": [],
            "sources": [],
            "graph_status": "up",
            "rag_status": "up",
        }
    return {
        "route": classify(question),
        "blocked": False,
        "block_message": None,
        "profile": profile,
    }


def _prepare(state: ChatState, deps: ChatDeps) -> dict[str, object]:
    route = state.get("route")
    question = str(state.get("question") or "")
    user_id = int(state["user_id"])
    if route == "recommend":
        try:
            result = deps.recommend(user_id, meal_from_question(question), "冰箱" in question)
        except Exception as exc:  # noqa: BLE001
            detail = getattr(exc, "detail", None)
            return {
                "recommend": None,
                "answer": _with_disclaimer(str(detail or "暂时无法推荐。")),
            }
        return {"recommend": result}
    if route == "report":
        scope = "weekly" if "周" in question else "daily"
        report = deps.load_report(user_id, scope)
        explain = deps.explain_report(user_id, scope)
        return {"report": report, "explain": explain}
    if route == "profile_update":
        return {"draft": extract_draft(question)}
    foods = _foods_in_question(question, deps.list_foods())
    names = [item.name for item in foods] or _fallback_names(question)
    relations: list[dict[str, object]] = []
    graph_status = "up"
    for name in names:
        status, links = deps.graph_links(name)
        if status != "up":
            graph_status = "down"
        relations.extend(links)
    rag_status, chunks = deps.retrieve(question)
    facts = [_food_fact(item) for item in foods]
    return {
        "facts": facts,
        "relations": relations,
        "chunks": chunks,
        "graph_status": graph_status,
        "rag_status": rag_status,
    }


def _respond(state: ChatState, _deps: ChatDeps) -> dict[str, object]:
    if state.get("blocked"):
        return {}
    route = state.get("route")
    if route == "help":
        return _help_answer(state)
    if route == "recommend":
        return _recommend_answer(state)
    if route == "report":
        return _report_answer(state)
    if route == "profile_update":
        draft = state.get("draft") or {}
        text = "我记下了这些信息，确认后才会写入档案。"
        if draft.get("allergies") or draft.get("dislikes"):
            text += _draft_text(draft)
        else:
            text += "请到健康档案页核对后再保存。"
        return {
            "answer": _with_disclaimer(text),
            "citation_ids": [],
            "sources": [],
        }
    return _knowledge_answer(state)


def _help_answer(state: ChatState) -> dict[str, object]:
    question = str(state.get("question") or "")
    context = guide_context(question)
    if not context:
        return {
            "answer": (
                "我还不清楚这个功能的操作。你可以问：怎么添加食材、怎么生成推荐、"
                "怎么填写健康档案、怎么转发报告、怎么设置大模型等。"
            ),
            "citation_ids": [],
            "sources": [],
        }
    try:
        raw = generate(
            [
                {"role": "system", "content": HELP_SYSTEM},
                {"role": "user", "content": json.dumps(
                    {"guide": context, "question": question}, ensure_ascii=False
                )},
            ],
            purpose="chat",
        )
        parsed = _parse_json(raw)
    except Exception:  # noqa: BLE001
        parsed = None
    if parsed and str(parsed.get("answer") or "").strip():
        return {"answer": str(parsed["answer"]).strip(), "citation_ids": [], "sources": []}
    return {"answer": context, "citation_ids": [], "sources": []}


def _knowledge_answer(state: ChatState) -> dict[str, object]:
    chunks = list(state.get("chunks") or [])
    facts = list(state.get("facts") or [])
    relations = list(state.get("relations") or [])
    fallback = _knowledge_template(facts, relations, bool(chunks))
    sources = _sources(chunks)
    chunk_ids = [str(item["chunk_id"]) for item in chunks if item.get("chunk_id")]
    payload = {"facts": facts, "relations": relations, "chunks": sources}
    try:
        raw = generate(
            [
                {"role": "system", "content": CHAT_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
            ],
            purpose="chat",
        )
        parsed = _parse_json(raw)
    except Exception:  # noqa: BLE001
        return {
            "answer": fallback,
            "citation_ids": chunk_ids,
            "sources": sources,
        }
    if parsed is None:
        return {"answer": fallback, "citation_ids": chunk_ids, "sources": sources}
    answer = str(parsed.get("answer") or "").strip()
    citations = parsed.get("citation_ids")
    if not answer or not isinstance(citations, list):
        return {"answer": fallback, "citation_ids": chunk_ids, "sources": sources}
    citation_text = [str(item) for item in citations]
    if any(item not in chunk_ids for item in citation_text):
        return {"answer": fallback, "citation_ids": chunk_ids, "sources": sources}
    if not _numbers_allowed(answer, payload):
        return {"answer": fallback, "citation_ids": chunk_ids, "sources": sources}
    return {
        "answer": _with_disclaimer(answer),
        "citation_ids": citation_text,
        "sources": sources,
    }


def _recommend_answer(state: ChatState) -> dict[str, object]:
    if state.get("answer"):
        return {"citation_ids": [], "sources": []}
    result = state.get("recommend") or {}
    if result.get("blocked"):
        return {
            "answer": _with_disclaimer(str(result.get("block_message") or "请就医或咨询医生、营养师。")),
            "citation_ids": [],
            "sources": [],
        }
    lines: list[str] = []
    for item in list(result.get("strict") or [])[:5]:
        if not isinstance(item, dict):
            continue
        reason = str(item.get("reason") or "")
        lines.append(f"{item.get('name')}。{reason}".strip())
    text = "可以考虑：" + " ".join(lines) if lines else "暂时没有可推荐的食谱。"
    citations: list[str] = []
    for item in list(result.get("strict") or []):
        if isinstance(item, dict):
            citations.extend(str(value) for value in item.get("citation_ids") or [])
    return {
        "answer": _with_disclaimer(text),
        "citation_ids": _unique(citations),
        "sources": [],
        "graph_status": result.get("graph") or "up",
        "rag_status": result.get("rag") or "up",
    }


def _report_answer(state: ChatState) -> dict[str, object]:
    explain = state.get("explain") or {}
    summary = str(explain.get("summary") or "暂时无法整理这份报告。")
    citations = [str(item) for item in explain.get("citation_ids") or []]
    return {
        "answer": _with_disclaimer(summary),
        "citation_ids": citations,
        "sources": [],
        "rag_status": explain.get("rag") or "up",
    }


def _knowledge_template(
    facts: list[dict[str, object]],
    relations: list[dict[str, object]],
    has_chunks: bool,
) -> str:
    parts: list[str] = []
    if relations:
        shown = relations[:6]
        bits = [
            f"{item.get('name')} { _RELATION.get(str(item.get('relation')), item.get('relation')) }"
            f" {item.get('other')}"
            for item in shown
            if isinstance(item, dict)
        ]
        parts.append("图谱关系：" + "；".join(str(item) for item in bits))
    else:
        parts.append("图谱里没有对应关系。")
    if facts:
        for item in facts:
            gi = item.get("gi")
            gi_text = "—" if gi is None else str(gi)
            parts.append(
                f"{item.get('name')} 的 GI 为 {gi_text}（{item.get('gi_source')}），数字来自成分表。"
            )
    if has_chunks:
        parts.append("依据见检索片段。")
    return _with_disclaimer("".join(parts))


def _foods_in_question(question: str, foods: list[FoodRecord]) -> list[FoodRecord]:
    ranked: list[tuple[int, int, FoodRecord]] = []
    for food in foods:
        for label in (food.name, *food.aliases):
            start = question.find(label)
            if start >= 0 and len(label) >= 2:
                ranked.append((len(label), start, food))
                break
    ranked.sort(key=lambda item: (-item[0], item[1]))
    chosen: list[FoodRecord] = []
    spans: list[tuple[int, int]] = []
    for length, start, food in ranked:
        end = start + length
        if any(start < used_end and end > used_start for used_start, used_end in spans):
            continue
        if any(item.food_id == food.food_id for item in chosen):
            continue
        chosen.append(food)
        spans.append((start, end))
    return chosen


def _fallback_names(question: str) -> list[str]:
    names: list[str] = []
    if "西瓜" in question:
        names.append("西瓜")
    if "糖尿病" in question:
        names.append("2型糖尿病")
    return names


def _food_fact(food: FoodRecord) -> dict[str, object]:
    return {
        "name": food.name,
        "gi": None if food.gi is None else _number(food.gi),
        "gi_source": food.gi_source or "待核对",
        "kcal": None if food.kcal is None else _number(food.kcal),
        "carb_g": None if food.carb_g is None else _number(food.carb_g),
    }


def _sources(chunks: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "chunk_id": chunk.get("chunk_id"),
            "source": chunk.get("source"),
            "page": chunk.get("page"),
            "text": chunk.get("text"),
        }
        for chunk in chunks
    ]


def _safe_profile(deps: ChatDeps, user_id: int) -> dict[str, object]:
    try:
        return deps.load_profile(user_id)
    except Exception:  # noqa: BLE001
        return {"diseases": [], "age": None}


def _with_disclaimer(text: str) -> str:
    cleaned = text.strip()
    if DISCLAIMER in cleaned:
        return cleaned
    return f"{cleaned}\n{DISCLAIMER}"


def _draft_text(draft: dict[str, object]) -> str:
    parts: list[str] = []
    allergies = draft.get("allergies") or []
    dislikes = draft.get("dislikes") or []
    if allergies:
        parts.append("过敏原：" + "、".join(str(item) for item in allergies))
    if dislikes:
        parts.append("不吃：" + "、".join(str(item) for item in dislikes))
    if not parts:
        return ""
    return "预览：" + "；".join(parts) + "。"


def _split(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[和与及、,，]", text) if part.strip()]


def _unique(items: list[str] | Any) -> list[str]:
    seen: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def _number(value: Decimal) -> float:
    return float(value)


def _parse_json(raw: str) -> dict[str, object] | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _numbers_allowed(text: str, payload: dict[str, object]) -> bool:
    allowed = _collect_numbers(payload)
    for match in _NUMBER.findall(text):
        if match not in allowed:
            return False
    return True


def _collect_numbers(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return found
    if isinstance(value, (int, float, Decimal)):
        text = format(Decimal(str(value)), "f").rstrip("0").rstrip(".")
        found.add(str(value))
        found.add(text)
        return found
    if isinstance(value, dict):
        for item in value.values():
            found.update(_collect_numbers(item))
        return found
    if isinstance(value, list):
        for item in value:
            found.update(_collect_numbers(item))
    return found
