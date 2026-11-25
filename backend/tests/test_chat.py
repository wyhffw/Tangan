"""问答路由、安全拦截和引用校验。不连接真实模型或向量库。"""

from collections.abc import Iterator
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.agent.chat import ChatDeps, FoodRecord, classify, extract_draft, run_chat
from app.agent.prompts import DISCLAIMER
from app.db.session import get_session
from app.main import app
from app.models.entities import User
from app.rules.engine import evaluate, reload_rules
from app.services import auth as auth_service
from app.services.chat import ChatError, answer_question, session_detail


def _food() -> FoodRecord:
    return FoodRecord(
        food_id=8,
        name="西瓜",
        aliases=(),
        gi=None,
        gi_source="待核对",
        kcal=Decimal(31),
        carb_g=Decimal("6.8"),
    )


def _deps(**overrides: object) -> ChatDeps:
    deps = ChatDeps(
        load_profile=lambda _user_id: {"diseases": ["2型糖尿病"], "age": 36},
        list_foods=lambda: [_food()],
        graph_links=lambda _name: (
            "up",
            [
                {
                    "name": "2型糖尿病",
                    "relation": "RECOMMEND",
                    "other": "西瓜",
                    "reason": "可适量水果",
                    "citation": "指南第13页",
                }
            ],
        ),
        retrieve=lambda _question: (
            "up",
            [
                {
                    "chunk_id": "g1",
                    "source": "guide.pdf",
                    "page": 13,
                    "text": "水果可适量食用",
                }
            ],
        ),
        recommend=lambda *_args: (_ for _ in ()).throw(AssertionError("recommend")),
        load_report=lambda *_args: (_ for _ in ()).throw(AssertionError("report")),
        explain_report=lambda *_args: (_ for _ in ()).throw(AssertionError("explain")),
    )
    for key, value in overrides.items():
        setattr(deps, key, value)
    return deps


def test_classify_four_routes() -> None:
    assert classify("糖尿病能吃西瓜吗") == "knowledge"
    assert classify("冰箱里有鸡蛋和番茄，晚上做什么？") == "recommend"
    assert classify("这周我碳水吃多了吗？") == "report"
    assert classify("我对虾过敏，不吃香菜") == "profile_update"


def test_safety_chest_pain_skips_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    reload_rules()
    called: list[str] = []

    def generate(*_args: object, **_kwargs: object) -> str:
        called.append("llm")
        return "{}"

    monkeypatch.setattr("app.agent.chat.generate", generate)
    result = run_chat(_deps(), user_id=2, question="我胸口疼怎么办")
    assert result["blocked"] is True
    assert result["route"] == "blocked"
    assert "请就医" in str(result["answer"])
    assert DISCLAIMER in str(result["answer"])
    assert called == []


def test_safety_kidney_pregnancy_and_dose() -> None:
    reload_rules()
    kidney = evaluate({"diseases": []}, user_text="肾病还能吃香蕉吗")
    pregnancy = evaluate({"diseases": []}, user_text="怀孕了怎么吃")
    dose = evaluate({"diseases": []}, user_text="二甲双胍的用药剂量是多少")
    assert kidney.blocked
    assert pregnancy.blocked
    assert dose.blocked
    assert all("请就医" in str(item.block_message) for item in (kidney, pregnancy, dose))


def test_safety_drug_name_and_dose_phrase() -> None:
    reload_rules()
    drug = evaluate({"diseases": []}, user_text="二甲双胍一次吃多少")
    insulin = evaluate({"diseases": []}, user_text="胰岛素每天打多少单位")
    assert drug.blocked
    assert insulin.blocked
    assert "请就医" in str(drug.block_message)


def test_knowledge_uses_graph_rag_and_disclaimer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.agent.chat.generate",
        lambda *_args, **_kwargs: (
            '{"answer":"西瓜可适量，GI 数字见成分表。","citation_ids":["g1"]}'
        ),
    )
    result = run_chat(_deps(), user_id=2, question="糖尿病能吃西瓜吗")
    assert result["route"] == "knowledge"
    assert result["blocked"] is False
    assert "西瓜" in str(result["answer"])
    assert result["citation_ids"] == ["g1"]
    assert result["sources"][0]["page"] == 13
    assert DISCLAIMER in str(result["answer"])


def test_unknown_citation_falls_back_to_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.agent.chat.generate",
        lambda *_args, **_kwargs: '{"answer":"可以天天猛吃。","citation_ids":["nope"]}',
    )
    result = run_chat(_deps(), user_id=2, question="糖尿病能吃西瓜吗")
    assert "依据见检索片段" in str(result["answer"])
    assert DISCLAIMER in str(result["answer"])


def test_chat_unavailable_falls_back_to_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.agent.chat.generate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("down")),
    )
    result = run_chat(_deps(), user_id=2, question="糖尿病能吃西瓜吗")
    assert "西瓜" in str(result["answer"])
    assert "图谱关系" in str(result["answer"])
    assert DISCLAIMER in str(result["answer"])


def test_recommend_route_does_not_call_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(
        "app.agent.chat.generate",
        lambda *_args, **_kwargs: called.append("llm") or "",
    )

    def recommend(_user_id: int, meal: str | None, only_inventory: bool) -> dict[str, object]:
        assert meal == "晚餐"
        assert only_inventory is True
        return {
            "graph": "up",
            "rag": "up",
            "blocked": False,
            "strict": [
                {
                    "name": "番茄炒蛋",
                    "reason": "含库存食材 番茄、鸡蛋",
                    "citation_ids": ["g2"],
                }
            ],
        }

    result = run_chat(_deps(recommend=recommend), user_id=2, question="冰箱里有鸡蛋和番茄，晚上做什么？")
    assert result["route"] == "recommend"
    assert "番茄炒蛋" in str(result["answer"])
    assert called == []
    assert DISCLAIMER in str(result["answer"])


def test_profile_update_does_not_write_the_profile() -> None:
    draft = extract_draft("我对虾过敏，不吃香菜")
    assert draft["allergies"] == ["虾"]
    assert draft["dislikes"] == ["香菜"]
    result = run_chat(_deps(), user_id=2, question="我对虾过敏，不吃香菜")
    assert result["route"] == "profile_update"
    assert result["draft"]["allergies"] == ["虾"]
    assert "确认后才会写入档案" in str(result["answer"])


def test_answer_question_persists_messages() -> None:
    db = MagicMock()
    chat = MagicMock(id=3, user_id=2)
    pending = MagicMock(id=9)
    db.get.return_value = chat
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()

    def add_session(_session: object, user_id: int) -> MagicMock:
        assert user_id == 2
        return chat

    captured: dict[str, object] = {}

    def add_message(_session: object, session_id: int, role: str, content: str, meta=None) -> None:
        captured.setdefault("roles", []).append(role)  # type: ignore[union-attr]
        captured[role] = {"content": content, "meta": meta or {}}

    monkey = pytest.MonkeyPatch()
    monkey.setattr("app.services.chat.add_session", add_session)
    monkey.setattr("app.services.chat.add_message", add_message)
    monkey.setattr("app.services.chat.add_pending", lambda *_args: pending)
    monkey.setattr("app.services.chat.get_session_for_user", lambda *_args: chat)
    monkey.setattr(
        "app.services.chat.run_chat",
        lambda *_args, **_kwargs: {
            "route": "knowledge",
            "blocked": False,
            "answer": f"西瓜可适量。\n{DISCLAIMER}",
            "citation_ids": ["g1"],
            "sources": [{"chunk_id": "g1", "source": "guide.pdf", "page": 13, "text": "水果"}],
            "graph": "up",
            "rag": "up",
            "draft": {},
        },
    )
    result = answer_question(db, 2, "糖尿病能吃西瓜吗")
    monkey.undo()
    assert result["session_id"] == 3
    assert captured["roles"] == ["user", "assistant"]
    db.commit.assert_called_once()


def test_other_user_session_is_hidden() -> None:
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(ChatError) as exc:
        session_detail(db, 2, 99)
    assert exc.value.status_code == 404


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    users: dict[int, User] = {}

    def get_by_username(_session: object, username: str) -> User | None:
        return next((user for user in users.values() if user.username == username), None)

    def get_by_id(_session: object, user_id: int) -> User | None:
        return users.get(user_id)

    def add_user(_session: object, user: User) -> User:
        user.id = len(users) + 1
        users[user.id] = user
        return user

    monkeypatch.setattr(auth_service, "get_by_username", get_by_username)
    monkeypatch.setattr(auth_service, "add_user", add_user)
    monkeypatch.setattr("app.api.deps.get_by_id", get_by_id)
    monkeypatch.setattr(
        "app.api.v1.chat.answer_question",
        lambda *_args, **_kwargs: {
            "session_id": 1,
            "route": "blocked",
            "blocked": True,
            "answer": "这个问题涉及用药、诊断或急症，请就医或咨询医生、营养师。\n" + DISCLAIMER,
            "citation_ids": [],
            "sources": [],
            "graph": "up",
            "rag": "up",
            "pending_profile_id": None,
            "draft": {},
        },
    )
    monkeypatch.setattr(
        "app.api.v1.chat.stream_events",
        lambda *_args, **_kwargs: iter(
            [
                '{"event":"token","text":"请就医"}\n',
                '{"event":"done","session_id":1,"route":"blocked"}\n',
            ]
        ),
    )

    def override_session() -> Iterator[MagicMock]:
        yield MagicMock()

    app.dependency_overrides[get_session] = override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _token(client: TestClient) -> str:
    created = client.post("/api/v1/auth/register", json={"username": "demo", "password": "secret"})
    assert created.status_code == 200
    logged = client.post("/api/v1/auth/login", json={"username": "demo", "password": "secret"})
    assert logged.status_code == 200
    return str(logged.json()["access_token"])


def test_chat_requires_token(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "糖尿病能吃西瓜吗"})
    stream = client.post("/api/v1/chat/stream", json={"message": "糖尿病能吃西瓜吗"})
    assert response.status_code == 401
    assert stream.status_code == 401


def test_chat_and_stream_endpoints(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {_token(client)}"}
    response = client.post(
        "/api/v1/chat",
        json={"message": "我胸口疼怎么办"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is True
    assert "请就医" in body["answer"]
    assert DISCLAIMER in body["answer"]
    stream = client.post(
        "/api/v1/chat/stream",
        json={"message": "我胸口疼怎么办"},
        headers=headers,
    )
    assert stream.status_code == 200
    assert "token" in stream.text
    assert "done" in stream.text


def _pending_answer(session: MagicMock, user_id: int, message: str) -> dict[str, object]:
    chat = MagicMock(id=3, user_id=user_id)
    pending = MagicMock(id=9, draft={"allergies": ["虾"], "dislikes": ["香菜"]})
    monkey = pytest.MonkeyPatch()
    monkey.setattr("app.services.chat.add_session", lambda *_args: chat)
    monkey.setattr("app.services.chat.get_session_for_user", lambda *_args: chat)
    monkey.setattr("app.services.chat.add_message", lambda *_args, **_kwargs: None)
    monkey.setattr("app.services.chat.get_latest_pending", lambda *_args: pending)
    monkey.setattr("app.services.chat.delete_pending", lambda *_args: None)
    result = answer_question(session, user_id, message)
    monkey.undo()
    return result


def test_pending_confirm_writes_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = MagicMock()
    profile.allergies = []
    profile.dislikes = []
    monkeypatch.setattr("app.services.chat.get_by_user_id", lambda *_args: profile)
    db = MagicMock()
    result = _pending_answer(db, 2, "确认")
    assert result["pending_profile_id"] is None
    assert "已写入档案" in str(result["answer"])
    assert profile.allergies == ["虾"]
    assert profile.dislikes == ["香菜"]


def test_pending_cancel_keeps_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.chat.get_by_user_id",
        lambda *_args: (_ for _ in ()).throw(AssertionError("取消不应写档案")),
    )
    db = MagicMock()
    result = _pending_answer(db, 2, "取消")
    assert result["pending_profile_id"] is None
    assert "已取消" in str(result["answer"])


def test_pending_correct_updates_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.chat.correct_draft",
        lambda *_args, **_kwargs: {"allergies": ["螃蟹"], "dislikes": []},
    )
    db = MagicMock()
    result = _pending_answer(db, 2, "不对，是对螃蟹过敏")
    assert result["pending_profile_id"] == 9
    assert "螃蟹" in str(result["answer"])
    assert result["draft"]["allergies"] == ["螃蟹"]
