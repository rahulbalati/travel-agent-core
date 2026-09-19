"""
Voyager AI - Application Entrypoint.
Configures FastAPI application, CORS middleware, and API routes.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

# Load .env into os.environ for native LangSmith / LangGraph auto-tracing
load_dotenv()

from app.config import get_settings
from app.api.routes import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("voyager.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Voyager AI starting up (Provider: %s, Model: %s)", settings.llm_provider, settings.model_name)
    yield
    logger.info("Voyager AI shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Agentic AI Travel Planner with LangGraph and Deterministic Guardrails.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
