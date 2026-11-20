"""导入全部模型，供 Alembic 发现表结构。"""

from app.models.entities import (
    AuditLog,
    ChatMessage,
    ChatSession,
    Food,
    FoodUnitConversion,
    HealthMetric,
    HealthProfile,
    InventoryItem,
    MealPlan,
    PendingProfileUpdate,
    Recipe,
    RecipeIngredient,
    RecommendLog,
    ShoppingItem,
    ShoppingList,
    User,
)

__all__ = [
    "AuditLog",
    "ChatMessage",
    "ChatSession",
    "Food",
    "FoodUnitConversion",
    "HealthMetric",
    "HealthProfile",
    "InventoryItem",
    "MealPlan",
    "PendingProfileUpdate",
    "Recipe",
    "RecipeIngredient",
    "RecommendLog",
    "ShoppingItem",
    "ShoppingList",
    "User",
]
