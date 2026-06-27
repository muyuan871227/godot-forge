"""GodotForge AI Services — FastAPI 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import (
    audiogen,
    build,
    codegen,
    community,
    education,
    enterprise,
    imagegen,
    marketplace,
    modelgen,
    npcai,
    projects,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[AI Services] Starting on port {settings.port}")
    print(f"[AI Services] LLM Provider: {settings.llm_provider}")
    yield
    print("[AI Services] Shutting down")


app = FastAPI(
    title="GodotForge AI Services",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(codegen.router, prefix="/api/v1/codegen", tags=["Code Generation"])
app.include_router(
    imagegen.router, prefix="/api/v1/imagegen", tags=["Image Generation"]
)
app.include_router(
    modelgen.router, prefix="/api/v1/modelgen", tags=["3D Model Generation"]
)
app.include_router(
    audiogen.router, prefix="/api/v1/audiogen", tags=["Audio Generation"]
)
app.include_router(npcai.router, prefix="/api/v1/npcai", tags=["NPC AI"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(projects.templates_router, prefix="/api/v1/templates", tags=["Templates"])
app.include_router(build.router, prefix="/api/v1/build", tags=["Build & Export"])
app.include_router(
    marketplace.router, prefix="/api/v1/marketplace", tags=["Marketplace"]
)
app.include_router(
    enterprise.router, prefix="/api/v1/enterprise", tags=["Enterprise"]
)
app.include_router(
    education.router, prefix="/api/v1/education", tags=["Education"]
)
app.include_router(
    community.router, prefix="/api/v1/community", tags=["Community"]
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
