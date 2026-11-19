"""6.5 质量评估：20 个用户画像的规则违反率、库存利用、平均响应时间。

云 LLM 无 Key，把 generate 换成无效内容，走模板降级（模拟云 LLM 不可用场景）。
每个画像都给同一份库存（番茄 + 鸡蛋），用来统计库存利用。
"""
import dataclasses
import json
import time

from app.agent import workflow as wf
from app.agent.workflow import StockItem, _hit_count, run_recommend
from app.db.session import get_sessionmaker
from app.services.recommend import default_deps

# 模拟云 LLM 不可用（无 Key）：返回无效内容，_explain_one 走模板降级
wf.generate = lambda *args, **kwargs: "{}"

PROFILES = [
    {"diseases": ["2型糖尿病"], "allergies": ["虾"], "dislikes": [], "age": 45},
    {"diseases": ["2型糖尿病"], "allergies": ["花生"], "dislikes": [], "age": 50},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": ["苦瓜"], "age": 38},
    {"diseases": ["2型糖尿病"], "allergies": ["牛奶"], "dislikes": ["辣椒"], "age": 42},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": [], "age": 55},
    {"diseases": ["2型糖尿病"], "allergies": ["鸡蛋"], "dislikes": [], "age": 47},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": ["肥肉"], "age": 60},
    {"diseases": ["2型糖尿病"], "allergies": ["海鲜"], "dislikes": [], "age": 35},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": ["内脏"], "age": 52},
    {"diseases": ["2型糖尿病"], "allergies": ["小麦"], "dislikes": [], "age": 44},
    {"diseases": [], "allergies": ["虾"], "dislikes": [], "age": 30},
    {"diseases": [], "allergies": [], "dislikes": ["香菜"], "age": 28},
    {"diseases": ["2型糖尿病", "妊娠"], "allergies": [], "dislikes": [], "age": 33},
    {"diseases": ["2型糖尿病", "肾病"], "allergies": [], "dislikes": [], "age": 48},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": [], "age": 16},
    {"diseases": ["2型糖尿病", "高血压"], "allergies": [], "dislikes": [], "age": 58},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": ["茄子"], "age": 40},
    {"diseases": ["2型糖尿病"], "allergies": ["大豆"], "dislikes": [], "age": 46},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": ["羊肉"], "age": 53},
    {"diseases": ["2型糖尿病"], "allergies": [], "dislikes": [], "age": 62},
]

STOCK_NAMES = ["番茄", "鸡蛋"]


def main() -> None:
    session = get_sessionmaker()()
    try:
        deps = default_deps(session)
        recipes = {r.recipe_id: r for r in deps.load_recipes()}
        catalog = sorted(deps.food_catalog)
        food_ids: dict[str, int] = {}
        for recipe in recipes.values():
            for ing in recipe.ingredients:
                food_ids.setdefault(ing.name, ing.food_id)
        stock = [
            StockItem(food_id=food_ids[name], name=name, expiring=False)
            for name in STOCK_NAMES
            if name in food_ids
        ]
        rows = []
        for idx, profile in enumerate(PROFILES, start=1):
            local_deps = dataclasses.replace(
                deps,
                load_profile=lambda _uid, p=profile: p,
                load_inventory=lambda _uid, s=stock: s,
            )
            started = time.perf_counter()
            try:
                resp = run_recommend(
                    local_deps,
                    user_id=1,
                    meal_type=None,
                    only_inventory=False,
                    exclude_ids=[],
                )
            except Exception as exc:  # noqa: BLE001
                rows.append(
                    {
                        "index": idx,
                        "profile": profile,
                        "error": str(exc),
                        "latency_ms": None,
                    }
                )
                continue
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            strict = list(resp.get("strict") or [])
            rejected = list(resp.get("rejected") or [])
            allergies = [str(x) for x in profile.get("allergies") or []]
            dislikes = [str(x) for x in profile.get("dislikes") or []]
            needles = allergies + dislikes
            violations = []
            held_count = 0
            held_examples = []
            for item in strict:
                cand = recipes.get(item.get("recipe_id"))
                if cand is not None and needles and _hit_count(cand, needles) > 0:
                    violations.append(item.get("name"))
                if item.get("held_foods"):
                    held_count += 1
                    held_examples.append(item.get("name"))
            rows.append(
                {
                    "index": idx,
                    "profile": profile,
                    "blocked": bool(resp.get("blocked")),
                    "block_message": resp.get("block_message"),
                    "strict_count": len(strict),
                    "rejected_count": len(rejected),
                    "violations": violations,
                    "held_count": held_count,
                    "held_examples": held_examples[:3],
                    "latency_ms": elapsed_ms,
                }
            )
        print(
            json.dumps(
                {
                    "catalog_size": len(catalog),
                    "stock": STOCK_NAMES,
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
