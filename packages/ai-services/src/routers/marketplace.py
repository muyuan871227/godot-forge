"""Marketplace — asset listings, browsing, reviews, and AI-to-marketplace publishing."""
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from .users import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MARKETPLACE_ROOT = Path(
    os.getenv("GODOTFORGE_MARKETPLACE_ROOT", "/tmp/godotforge/marketplace")
)
LISTINGS_FILE = MARKETPLACE_ROOT / "listings.json"
REVIEWS_FILE = MARKETPLACE_ROOT / "reviews.json"
PROJECTS_ROOT = Path(
    os.getenv("GODOTFORGE_PROJECTS_ROOT", "/tmp/godotforge/projects")
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AssetListing(BaseModel):
    """A marketplace asset listing."""

    id: str = ""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(
        ...,
        pattern=r"^(sprite|tilemap|character|environment|ui|audio|model3d|effect|script|plugin|template|other)$",
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    price: float = Field(default=0.0, ge=0.0, description="Price in USD, 0 for free")
    license: str = Field(default="MIT", max_length=64)
    godot_version: str = Field(default="4.4", max_length=16)

    # Files
    preview_url: str = ""
    download_url: str = ""
    file_size: int = 0

    # AI generation metadata (set when published from AI pipeline)
    ai_generated: bool = False
    ai_provider: str = ""
    ai_prompt: str = ""

    # Author (set server-side)
    author_id: str = ""
    author_name: str = ""

    # Stats (set server-side)
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0

    # Timestamps (set server-side)
    created_at: str = ""
    updated_at: str = ""


class ListingResponse(BaseModel):
    """Response wrapper for listing queries."""

    listings: list[AssetListing]
    total: int
    page: int
    page_size: int


class CreateListingRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(
        ...,
        pattern=r"^(sprite|tilemap|character|environment|ui|audio|model3d|effect|script|plugin|template|other)$",
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    price: float = Field(default=0.0, ge=0.0)
    license: str = Field(default="MIT", max_length=64)
    godot_version: str = Field(default="4.4", max_length=16)
    preview_url: str = ""
    download_url: str = ""
    file_size: int = 0


class AIPublishRequest(BaseModel):
    """Request to publish an AI-generated asset to the marketplace."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(
        ...,
        pattern=r"^(sprite|tilemap|character|environment|ui|audio|model3d|effect|script|plugin|template|other)$",
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    price: float = Field(default=0.0, ge=0.0)
    license: str = Field(default="MIT", max_length=64)
    godot_version: str = Field(default="4.4", max_length=16)

    # AI-specific fields
    ai_provider: str = Field(..., description="Which AI provider generated this asset")
    ai_prompt: str = Field(..., description="The prompt used to generate the asset")
    source_project_id: str = Field(default="", description="Project the asset was generated in")
    source_file_path: str = Field(default="", description="Relative path to the asset in the project")


class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


class ReviewResponse(BaseModel):
    id: str
    listing_id: str
    user_id: str
    username: str
    rating: int
    comment: str
    created_at: str


class ImportRequest(BaseModel):
    project_id: str = Field(..., description="Target project ID")
    target_path: str = Field(
        default="", description="Optional path within the project to import into"
    )


# ---------------------------------------------------------------------------
# JSON store helpers
# ---------------------------------------------------------------------------


def _ensure_marketplace_dir() -> None:
    MARKETPLACE_ROOT.mkdir(parents=True, exist_ok=True)
    # Assets storage directory
    (MARKETPLACE_ROOT / "assets").mkdir(exist_ok=True)


def _load_listings() -> list[dict]:
    _ensure_marketplace_dir()
    if not LISTINGS_FILE.exists():
        LISTINGS_FILE.write_text("[]")
        return []
    try:
        data = json.loads(LISTINGS_FILE.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_listings(listings: list[dict]) -> None:
    _ensure_marketplace_dir()
    LISTINGS_FILE.write_text(json.dumps(listings, indent=2, ensure_ascii=False))


def _find_listing(listing_id: str) -> dict | None:
    for lst in _load_listings():
        if lst["id"] == listing_id:
            return lst
    return None


def _update_listing(listing_id: str, updates: dict) -> dict | None:
    listings = _load_listings()
    for lst in listings:
        if lst["id"] == listing_id:
            lst.update(updates)
            lst["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_listings(listings)
            return lst
    return None


def _load_reviews() -> list[dict]:
    _ensure_marketplace_dir()
    if not REVIEWS_FILE.exists():
        REVIEWS_FILE.write_text("[]")
        return []
    try:
        data = json.loads(REVIEWS_FILE.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_reviews(reviews: list[dict]) -> None:
    _ensure_marketplace_dir()
    REVIEWS_FILE.write_text(json.dumps(reviews, indent=2, ensure_ascii=False))


def _recalculate_rating(listing_id: str) -> tuple[float, int]:
    """Recalculate average rating for a listing from all its reviews."""
    reviews = _load_reviews()
    listing_reviews = [r for r in reviews if r["listing_id"] == listing_id]
    if not listing_reviews:
        return 0.0, 0
    total = sum(r["rating"] for r in listing_reviews)
    count = len(listing_reviews)
    avg = round(total / count, 2)
    return avg, count


# ---------------------------------------------------------------------------
# Routes — Listings CRUD
# ---------------------------------------------------------------------------


@router.post("/listings", response_model=AssetListing, status_code=status.HTTP_201_CREATED)
async def create_listing(
    body: CreateListingRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new marketplace listing."""
    now = datetime.now(timezone.utc).isoformat()
    listing_id = uuid.uuid4().hex[:12]

    listing = AssetListing(
        id=listing_id,
        title=body.title,
        description=body.description,
        category=body.category,
        tags=body.tags,
        price=body.price,
        license=body.license,
        godot_version=body.godot_version,
        preview_url=body.preview_url,
        download_url=body.download_url,
        file_size=body.file_size,
        ai_generated=False,
        author_id=user["id"],
        author_name=user.get("display_name", user["username"]),
        downloads=0,
        rating=0.0,
        rating_count=0,
        created_at=now,
        updated_at=now,
    )

    listings = _load_listings()
    listings.append(listing.model_dump())
    _save_listings(listings)

    return listing


@router.get("/listings", response_model=ListingResponse)
async def browse_listings(
    category: str = Query(default="", description="Filter by category"),
    search: str = Query(default="", description="Search in title, description, tags"),
    sort: str = Query(
        default="newest",
        pattern=r"^(newest|popular|rating|price_asc|price_desc)$",
        description="Sort order",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    ai_generated: bool | None = Query(default=None, description="Filter by AI-generated flag"),
    min_rating: float = Query(default=0.0, ge=0.0, le=5.0, description="Minimum rating"),
    free_only: bool = Query(default=False, description="Only show free assets"),
):
    """Browse marketplace listings with filtering, search, and pagination."""
    listings = _load_listings()

    # Filter by category
    if category:
        listings = [lst for lst in listings if lst.get("category") == category]

    # Filter by AI-generated flag
    if ai_generated is not None:
        listings = [lst for lst in listings if lst.get("ai_generated") == ai_generated]

    # Filter by minimum rating
    if min_rating > 0:
        listings = [lst for lst in listings if lst.get("rating", 0) >= min_rating]

    # Filter free only
    if free_only:
        listings = [lst for lst in listings if lst.get("price", 0) == 0]

    # Search
    if search.strip():
        lower_search = search.lower()
        filtered = []
        for lst in listings:
            searchable = " ".join(
                [
                    lst.get("title", ""),
                    lst.get("description", ""),
                    " ".join(lst.get("tags", [])),
                    lst.get("author_name", ""),
                ]
            ).lower()
            if lower_search in searchable:
                filtered.append(lst)
        listings = filtered

    total = len(listings)

    # Sort
    if sort == "newest":
        listings.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort == "popular":
        listings.sort(key=lambda x: x.get("downloads", 0), reverse=True)
    elif sort == "rating":
        listings.sort(key=lambda x: x.get("rating", 0), reverse=True)
    elif sort == "price_asc":
        listings.sort(key=lambda x: x.get("price", 0))
    elif sort == "price_desc":
        listings.sort(key=lambda x: x.get("price", 0), reverse=True)

    # Paginate
    offset = (page - 1) * page_size
    paginated = listings[offset : offset + page_size]

    return ListingResponse(
        listings=[AssetListing(**lst) for lst in paginated],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/listings/{listing_id}", response_model=AssetListing)
async def get_listing(listing_id: str):
    """Get a single listing by ID."""
    listing = _find_listing(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found"
        )
    return AssetListing(**listing)


# ---------------------------------------------------------------------------
# Routes — Download & Import
# ---------------------------------------------------------------------------


@router.post("/listings/{listing_id}/download")
async def download_listing(
    listing_id: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Record a download and return the download URL for the asset.

    In a production system this would generate a signed, time-limited URL.
    For dev we just return the stored download_url and bump the counter.
    """
    listing = _find_listing(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found"
        )

    # Increment download counter
    listings = _load_listings()
    for lst in listings:
        if lst["id"] == listing_id:
            lst["downloads"] = lst.get("downloads", 0) + 1
            break
    _save_listings(listings)

    return {
        "listing_id": listing_id,
        "download_url": listing.get("download_url", ""),
        "file_size": listing.get("file_size", 0),
        "message": "Download started",
    }


@router.post("/listings/{listing_id}/import")
async def import_to_project(
    listing_id: str,
    body: ImportRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Import a marketplace asset into a Godot project.

    Copies the asset files from marketplace storage into the target project
    directory. In production this would stream from an object store; for dev
    we copy from the local marketplace assets folder.
    """
    listing = _find_listing(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found"
        )

    # Verify the target project exists
    project_dir = PROJECTS_ROOT / user["id"] / body.project_id
    if not project_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target project not found"
        )

    # Determine target path inside the project
    import_dir = project_dir
    if body.target_path:
        import_dir = project_dir / body.target_path
        # Prevent path traversal
        if not str(import_dir.resolve()).startswith(str(project_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Path traversal not allowed",
            )
    import_dir.mkdir(parents=True, exist_ok=True)

    # Copy asset files from marketplace storage
    asset_dir = MARKETPLACE_ROOT / "assets" / listing_id
    imported_files: list[str] = []

    if asset_dir.is_dir():
        for file_path in asset_dir.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(asset_dir)
                dest = import_dir / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest)
                imported_files.append(str(relative))
    else:
        # No local files — in production we'd download from the URL
        pass

    # Bump download counter
    listings = _load_listings()
    for lst in listings:
        if lst["id"] == listing_id:
            lst["downloads"] = lst.get("downloads", 0) + 1
            break
    _save_listings(listings)

    return {
        "listing_id": listing_id,
        "project_id": body.project_id,
        "imported_files": imported_files,
        "import_path": str(import_dir.relative_to(project_dir)),
        "message": f"Imported {len(imported_files)} files into project",
    }


# ---------------------------------------------------------------------------
# Routes — AI-to-Marketplace publishing
# ---------------------------------------------------------------------------


@router.post(
    "/ai-to-marketplace", response_model=AssetListing, status_code=status.HTTP_201_CREATED
)
async def publish_ai_asset(
    body: AIPublishRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Publish an AI-generated asset to the marketplace.

    Takes the asset from a project (where it was generated by an AI pipeline),
    copies it to marketplace storage, and creates a listing.
    """
    now = datetime.now(timezone.utc).isoformat()
    listing_id = uuid.uuid4().hex[:12]

    # If a source project + file path is provided, copy the asset to marketplace storage
    asset_dir = MARKETPLACE_ROOT / "assets" / listing_id
    file_size = 0

    if body.source_project_id and body.source_file_path:
        project_dir = PROJECTS_ROOT / user["id"] / body.source_project_id
        source_file = project_dir / body.source_file_path

        if not str(source_file.resolve()).startswith(str(project_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Path traversal not allowed",
            )

        if not source_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source file not found: {body.source_file_path}",
            )

        asset_dir.mkdir(parents=True, exist_ok=True)

        if source_file.is_file():
            dest = asset_dir / source_file.name
            shutil.copy2(source_file, dest)
            file_size = source_file.stat().st_size
        elif source_file.is_dir():
            shutil.copytree(source_file, asset_dir, dirs_exist_ok=True)
            file_size = sum(f.stat().st_size for f in source_file.rglob("*") if f.is_file())

    listing = AssetListing(
        id=listing_id,
        title=body.title,
        description=body.description,
        category=body.category,
        tags=body.tags,
        price=body.price,
        license=body.license,
        godot_version=body.godot_version,
        preview_url="",
        download_url=f"/marketplace/assets/{listing_id}",
        file_size=file_size,
        ai_generated=True,
        ai_provider=body.ai_provider,
        ai_prompt=body.ai_prompt,
        author_id=user["id"],
        author_name=user.get("display_name", user["username"]),
        downloads=0,
        rating=0.0,
        rating_count=0,
        created_at=now,
        updated_at=now,
    )

    listings = _load_listings()
    listings.append(listing.model_dump())
    _save_listings(listings)

    return listing


# ---------------------------------------------------------------------------
# Routes — Reviews
# ---------------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_review(
    listing_id: str,
    body: ReviewRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Add a review/rating to a listing.

    A user can only leave one review per listing. Submitting again replaces
    the previous review.
    """
    listing = _find_listing(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found"
        )

    # Don't allow authors to review their own listings
    if listing.get("author_id") == user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot review your own listing",
        )

    now = datetime.now(timezone.utc).isoformat()
    reviews = _load_reviews()

    # Check for existing review by this user on this listing
    existing_idx = None
    for idx, review in enumerate(reviews):
        if review["listing_id"] == listing_id and review["user_id"] == user["id"]:
            existing_idx = idx
            break

    review_data = {
        "id": uuid.uuid4().hex[:12],
        "listing_id": listing_id,
        "user_id": user["id"],
        "username": user.get("display_name", user["username"]),
        "rating": body.rating,
        "comment": body.comment,
        "created_at": now,
    }

    if existing_idx is not None:
        # Preserve original review ID and creation date
        review_data["id"] = reviews[existing_idx]["id"]
        review_data["created_at"] = reviews[existing_idx]["created_at"]
        reviews[existing_idx] = review_data
    else:
        reviews.append(review_data)

    _save_reviews(reviews)

    # Recalculate listing rating
    avg_rating, rating_count = _recalculate_rating(listing_id)
    _update_listing(listing_id, {"rating": avg_rating, "rating_count": rating_count})

    return ReviewResponse(**review_data)


@router.get("/listings/{listing_id}/reviews", response_model=list[ReviewResponse])
async def get_reviews(listing_id: str):
    """Get all reviews for a listing."""
    listing = _find_listing(listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found"
        )

    reviews = _load_reviews()
    listing_reviews = [r for r in reviews if r["listing_id"] == listing_id]
    listing_reviews.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    return [ReviewResponse(**r) for r in listing_reviews]
