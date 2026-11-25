"""个体化营养目标、餐次分配与碳水计数。

每日热量复用 services/nutrition.py 的理想体重估算法；三大营养素供能比
按《中国糖尿病医学营养治疗指南（2022 版）》推荐的碳水化合物 45%～60%、
蛋白质 15%～20%、脂肪 20%～35% 取中值 50% / 18% / 32%。三餐热量按
30% / 40% / 30% 分配（加餐不单列预算）。碳水计数按 1 份碳水 = 15 克。

这些比例和换算用于膳食规划展示，不是临床营养处方，来源均标注「待核对」。
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services.nutrition import suggested_daily_kcal

CARB_RATIO = Decimal("0.50")
PROTEIN_RATIO = Decimal("0.18")
FAT_RATIO = Decimal("0.32")
CARB_KCAL_PER_G = Decimal("4")
PROTEIN_KCAL_PER_G = Decimal("4")
FAT_KCAL_PER_G = Decimal("9")
CARB_SERVING_G = Decimal("15")

MEAL_SHARES = {
    "早餐": Decimal("0.30"),
    "午餐": Decimal("0.40"),
    "晚餐": Decimal("0.30"),
}

MACRO_SOURCE = "《中国糖尿病医学营养治疗指南（2022版）》三大营养素供能比，取中值；待核对"
MEAL_SPLIT_SOURCE = "三餐热量 30%/40%/30%；待核对"
CARB_SERVING_SOURCE = "1 份碳水 = 15 克"

_QUANTUM = Decimal("0.01")

FBG_ELEVATED = Decimal("6.1")
FBG_HIGH = Decimal("7.0")
HBA1C_ELEVATED = Decimal("6.5")
HBA1C_HIGH = Decimal("7.5")
GLUCOSE_SOURCE = "空腹血糖/糖化偏高时碳水比例收紧；待核对"

_CARB_SCALES = {
    "normal": Decimal("1.00"),
    "elevated": Decimal("0.85"),
    "high": Decimal("0.75"),
}


@dataclass(frozen=True)
class DailyTargets:
    daily_kcal: int
    carb_g: Decimal
    protein_g: Decimal
    fat_g: Decimal
    macro_source: str
    meal_split_source: str


@dataclass(frozen=True)
class MealTargets:
    meal_type: str
    kcal: Decimal
    carb_g: Decimal
    protein_g: Decimal
    fat_g: Decimal


@dataclass(frozen=True)
class GlucoseStatus:
    level: str
    fasting_glucose: float | None
    hba1c: float | None
    carb_scale: Decimal
    source: str


def daily_targets(
    height_cm: Decimal | None,
    weight_kg: Decimal | None,
    activity_level: str | None,
    carb_scale: Decimal = Decimal("1.00"),
) -> DailyTargets | None:
    estimate = suggested_daily_kcal(height_cm, weight_kg, activity_level)
    if estimate is None:
        return None
    daily = Decimal(estimate.suggested_kcal)
    return DailyTargets(
        daily_kcal=estimate.suggested_kcal,
        carb_g=_grams(daily, CARB_RATIO * carb_scale, CARB_KCAL_PER_G),
        protein_g=_grams(daily, PROTEIN_RATIO, PROTEIN_KCAL_PER_G),
        fat_g=_grams(daily, FAT_RATIO, FAT_KCAL_PER_G),
        macro_source=MACRO_SOURCE,
        meal_split_source=MEAL_SPLIT_SOURCE,
    )


def meal_targets(targets: DailyTargets, meal_type: str | None) -> MealTargets | None:
    if meal_type is None:
        return None
    share = MEAL_SHARES.get(meal_type)
    if share is None:
        return None
    return MealTargets(
        meal_type=meal_type,
        kcal=_share(targets.daily_kcal, share),
        carb_g=_share(targets.carb_g, share),
        protein_g=_share(targets.protein_g, share),
        fat_g=_share(targets.fat_g, share),
    )


def carb_servings(carb_g: Decimal | None) -> float | None:
    if carb_g is None:
        return None
    doubled = (carb_g / CARB_SERVING_G * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(doubled / 2)


def _grams(daily_kcal: Decimal, ratio: Decimal, kcal_per_g: Decimal) -> Decimal:
    return _quantize(daily_kcal * ratio / kcal_per_g)


def _share(value: Decimal | int, share: Decimal) -> Decimal:
    return _quantize(Decimal(value) * share)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


def glucose_status(
    fasting_glucose: Decimal | None,
    hba1c: Decimal | None,
) -> GlucoseStatus:
    """按空腹血糖和糖化血红蛋白判断碳水收紧档位。

    阈值取常见参考区间（空腹血糖 6.1 / 7.0 mmol/L，糖化 6.5 / 7.5 %），
    用于膳食规划展示，不是临床诊断，来源待核对。
    """
    level = "normal"
    for value, elevated_at, high_at in (
        (fasting_glucose, FBG_ELEVATED, FBG_HIGH),
        (hba1c, HBA1C_ELEVATED, HBA1C_HIGH),
    ):
        if value is None:
            continue
        if value >= high_at:
            level = "high"
        elif value >= elevated_at and level == "normal":
            level = "elevated"
    return GlucoseStatus(
        level=level,
        fasting_glucose=_to_float(fasting_glucose),
        hba1c=_to_float(hba1c),
        carb_scale=_CARB_SCALES[level],
        source=GLUCOSE_SOURCE,
    )


def _to_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)
