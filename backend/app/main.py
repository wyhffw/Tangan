from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.agent.workflow import RecommendError
from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.graph import router as graph_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.llm_config import router as llm_config_router
from app.api.v1.meal_plans import router as meal_plans_router
from app.api.v1.profile import router as profile_router
from app.api.v1.recipes import router as recipes_router
from app.api.v1.recommend import router as recommend_router
from app.api.v1.reports import router as reports_router
from app.api.v1.shopping import router as shopping_router
from app.core.health import health_payload
from app.core.logging_setup import setup_logging
from app.middleware.request_id import RequestIdMiddleware
from app.rules.engine import RulesError
from app.services.auth import AuthError
from app.services.chat import ChatError
from app.services.graph import GraphError
from app.services.inventory import (
    InventoryError,
    start_expiry_scheduler,
    stop_expiry_scheduler,
)
from app.services.meal_plans import MealPlanError
from app.services.profile import ProfileError
from app.services.recipes import RecipeError
from app.services.recommend import RecommendDataError
from app.services.shopping import ShoppingError

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    start_expiry_scheduler()
    yield
    stop_expiry_scheduler()


app = FastAPI(title="糖安食助", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(llm_config_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")
app.include_router(recipes_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(shopping_router, prefix="/api/v1")
app.include_router(meal_plans_router, prefix="/api/v1")


@app.exception_handler(AuthError)
async def handle_auth_error(_request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(ChatError)
async def handle_chat_error(_request: Request, exc: ChatError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(GraphError)
async def handle_graph_error(_request: Request, exc: GraphError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(ProfileError)
async def handle_profile_error(_request: Request, exc: ProfileError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(InventoryError)
async def handle_inventory_error(
    _request: Request, exc: InventoryError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(RecommendDataError)
async def handle_recommend_data_error(
    _request: Request, exc: RecommendDataError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(RecommendError)
async def handle_recommend_error(
    _request: Request, exc: RecommendError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(RecipeError)
async def handle_recipe_error(_request: Request, exc: RecipeError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(MealPlanError)
async def handle_meal_plan_error(
    _request: Request, exc: MealPlanError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(ShoppingError)
async def handle_shopping_error(
    _request: Request, exc: ShoppingError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(RulesError)
async def handle_rules_error(_request: Request, _exc: RulesError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "规则暂时不可用", "code": "rules_unavailable"},
    )


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return health_payload()
