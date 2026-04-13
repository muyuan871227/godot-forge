"""Enterprise API — model training, batch generation, analytics, and audit logging."""
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from .users import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENTERPRISE_DATA_DIR = Path(
    os.getenv("GODOTFORGE_ENTERPRISE_DATA_DIR", "/tmp/godotforge/enterprise")
)
AUDIT_LOG_FILE = ENTERPRISE_DATA_DIR / "audit_log.jsonl"
TRAINING_JOBS_FILE = ENTERPRISE_DATA_DIR / "training_jobs.json"
BATCH_JOBS_FILE = ENTERPRISE_DATA_DIR / "batch_jobs.json"
USAGE_FILE = ENTERPRISE_DATA_DIR / "usage.json"


def _ensure_enterprise_store() -> None:
    ENTERPRISE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in (TRAINING_JOBS_FILE, BATCH_JOBS_FILE, USAGE_FILE):
        if not f.exists():
            f.write_text("[]")
    if not AUDIT_LOG_FILE.exists():
        AUDIT_LOG_FILE.write_text("")


def _load_json(path: Path) -> list[dict]:
    _ensure_enterprise_store()
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_json(path: Path, data: list[dict]) -> None:
    _ensure_enterprise_store()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _append_audit(action: str, user_id: str, details: dict[str, Any] | None = None) -> None:
    _ensure_enterprise_store()
    entry = {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "action": action,
        "details": details or {},
    }
    with AUDIT_LOG_FILE.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class TrainingStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class TrainModelRequest(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=128, description="Name for the fine-tuned model")
    base_model: str = Field(
        default="deepseek-coder-v2:16b",
        description="Base model to fine-tune (must be available in Ollama)",
    )
    dataset_path: str = Field(..., description="Path or S3 URI to the training dataset (JSONL)")
    epochs: int = Field(default=3, ge=1, le=50, description="Number of training epochs")
    learning_rate: float = Field(default=2e-5, gt=0, lt=1, description="Learning rate")
    batch_size: int = Field(default=4, ge=1, le=64, description="Training batch size")
    max_seq_length: int = Field(default=2048, ge=128, le=8192, description="Maximum sequence length")
    description: str = Field(default="", max_length=512)


class TrainModelResponse(BaseModel):
    job_id: str
    status: TrainingStatus
    model_name: str
    created_at: str
    message: str


class BatchAssetType(str, Enum):
    sprite = "sprite"
    tilemap = "tilemap"
    character = "character"
    environment = "environment"
    audio_sfx = "audio_sfx"
    audio_bgm = "audio_bgm"
    model_3d = "model_3d"
    script = "script"


class BatchItem(BaseModel):
    asset_type: BatchAssetType
    prompt: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict, description="Type-specific parameters")


class BatchGenerateRequest(BaseModel):
    items: list[BatchItem] = Field(..., min_length=1, max_length=500)
    project_id: str = Field(default="", description="Optional project to associate assets with")
    priority: int = Field(default=0, ge=0, le=10, description="Queue priority (0=normal, 10=urgent)")
    webhook_url: str = Field(default="", description="URL to POST results to when complete")


class BatchJobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    partially_failed = "partially_failed"
    failed = "failed"


class BatchGenerateResponse(BaseModel):
    job_id: str
    status: BatchJobStatus
    total_items: int
    created_at: str
    message: str


class UsageAnalyticsResponse(BaseModel):
    period_start: str
    period_end: str
    total_requests: int
    requests_by_type: dict[str, int]
    total_tokens_used: int
    total_images_generated: int
    total_models_generated: int
    total_audio_generated: int
    total_training_jobs: int
    active_users: int
    storage_used_mb: float


class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    user_id: str
    action: str
    details: dict[str, Any]


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/train-model", response_model=TrainModelResponse, status_code=status.HTTP_202_ACCEPTED)
async def train_model(
    req: TrainModelRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Trigger custom model fine-tuning.

    Queues a training job that fine-tunes the specified base model on the
    provided dataset.  The job runs asynchronously on the model-training
    worker service.
    """
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "job_id": job_id,
        "status": TrainingStatus.queued,
        "model_name": req.model_name,
        "base_model": req.base_model,
        "dataset_path": req.dataset_path,
        "epochs": req.epochs,
        "learning_rate": req.learning_rate,
        "batch_size": req.batch_size,
        "max_seq_length": req.max_seq_length,
        "description": req.description,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }

    jobs = _load_json(TRAINING_JOBS_FILE)
    jobs.append(job)
    _save_json(TRAINING_JOBS_FILE, jobs)

    _append_audit("train_model.queued", current_user["id"], {"job_id": job_id, "model_name": req.model_name})

    return TrainModelResponse(
        job_id=job_id,
        status=TrainingStatus.queued,
        model_name=req.model_name,
        created_at=now,
        message=f"Training job queued. Model '{req.model_name}' will be fine-tuned from '{req.base_model}'.",
    )


@router.get("/train-model/{job_id}", response_model=TrainModelResponse)
async def get_training_job(
    job_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get the status of a training job."""
    jobs = _load_json(TRAINING_JOBS_FILE)
    for job in jobs:
        if job["job_id"] == job_id:
            return TrainModelResponse(
                job_id=job["job_id"],
                status=job["status"],
                model_name=job["model_name"],
                created_at=job["created_at"],
                message=f"Job is {job['status']}.",
            )
    raise HTTPException(status_code=404, detail="Training job not found")


@router.post("/batch-generate", response_model=BatchGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_generate(
    req: BatchGenerateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Submit a batch asset generation job.

    Accepts up to 500 asset generation requests in a single call.
    Each item specifies an asset type, a prompt, and optional
    type-specific parameters.  Results are available via polling
    or delivered to the optional webhook URL.
    """
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "job_id": job_id,
        "status": BatchJobStatus.queued,
        "total_items": len(req.items),
        "completed_items": 0,
        "failed_items": 0,
        "items": [item.model_dump() for item in req.items],
        "project_id": req.project_id,
        "priority": req.priority,
        "webhook_url": req.webhook_url,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }

    jobs = _load_json(BATCH_JOBS_FILE)
    jobs.append(job)
    _save_json(BATCH_JOBS_FILE, jobs)

    _append_audit(
        "batch_generate.queued",
        current_user["id"],
        {"job_id": job_id, "total_items": len(req.items)},
    )

    return BatchGenerateResponse(
        job_id=job_id,
        status=BatchJobStatus.queued,
        total_items=len(req.items),
        created_at=now,
        message=f"Batch generation queued with {len(req.items)} item(s).",
    )


@router.get("/batch-generate/{job_id}", response_model=BatchGenerateResponse)
async def get_batch_job(
    job_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get the status of a batch generation job."""
    jobs = _load_json(BATCH_JOBS_FILE)
    for job in jobs:
        if job["job_id"] == job_id:
            return BatchGenerateResponse(
                job_id=job["job_id"],
                status=job["status"],
                total_items=job["total_items"],
                created_at=job["created_at"],
                message=f"Completed {job.get('completed_items', 0)}/{job['total_items']} items.",
            )
    raise HTTPException(status_code=404, detail="Batch job not found")


@router.get("/usage-analytics", response_model=UsageAnalyticsResponse)
async def usage_analytics(
    current_user: Annotated[dict, Depends(get_current_user)],
    period: str = Query(
        default="30d",
        description="Time period: 7d, 30d, 90d, 1y, or custom ISO range start..end",
    ),
):
    """Return usage statistics for the deployment.

    Provides aggregated metrics including request counts by type,
    token usage, asset generation counts, and storage utilisation.
    """
    now = datetime.now(timezone.utc).isoformat()

    _append_audit("usage_analytics.viewed", current_user["id"], {"period": period})

    # In production this queries the database; here we return a representative stub.
    return UsageAnalyticsResponse(
        period_start=now,
        period_end=now,
        total_requests=0,
        requests_by_type={
            "codegen": 0,
            "imagegen": 0,
            "modelgen": 0,
            "audiogen": 0,
            "npcai": 0,
        },
        total_tokens_used=0,
        total_images_generated=0,
        total_models_generated=0,
        total_audio_generated=0,
        total_training_jobs=len(_load_json(TRAINING_JOBS_FILE)),
        active_users=0,
        storage_used_mb=0.0,
    )


@router.get("/audit-log", response_model=AuditLogResponse)
async def audit_log(
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    action_filter: str = Query(default="", description="Filter by action prefix, e.g. 'train_model'"),
    user_filter: str = Query(default="", description="Filter by user ID"),
):
    """Return the audit trail for the deployment.

    Every mutating enterprise action is recorded with a timestamp, user,
    action type, and JSON details payload.
    """
    _ensure_enterprise_store()

    entries: list[dict] = []
    try:
        for line in AUDIT_LOG_FILE.read_text().strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if action_filter and not entry.get("action", "").startswith(action_filter):
                continue
            if user_filter and entry.get("user_id") != user_filter:
                continue
            entries.append(entry)
    except (json.JSONDecodeError, OSError):
        entries = []

    total = len(entries)
    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]

    _append_audit("audit_log.viewed", current_user["id"])

    return AuditLogResponse(
        entries=[AuditLogEntry(**e) for e in page_entries],
        total=total,
        page=page,
        page_size=page_size,
    )
