"""Community system — game publishing, ratings, and game jams."""
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from .users import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COMMUNITY_DATA_DIR = Path(
    os.getenv("GODOTFORGE_COMMUNITY_DATA_DIR", "/tmp/godotforge/community")
)
GAMES_FILE = COMMUNITY_DATA_DIR / "games.json"
RATINGS_FILE = COMMUNITY_DATA_DIR / "ratings.json"
GAMEJAMS_FILE = COMMUNITY_DATA_DIR / "gamejams.json"
JAM_ENTRIES_FILE = COMMUNITY_DATA_DIR / "jam_entries.json"


def _ensure_store() -> None:
    COMMUNITY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in (GAMES_FILE, RATINGS_FILE, GAMEJAMS_FILE, JAM_ENTRIES_FILE):
        if not f.exists():
            f.write_text("[]")


def _load_json(path: Path) -> list[dict]:
    _ensure_store()
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_json(path: Path, data: list[dict]) -> None:
    _ensure_store()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class GameSortField(str, Enum):
    newest = "newest"
    top_rated = "top_rated"
    most_played = "most_played"


class PublishGameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=4096)
    web_url: str = Field(default="", description="URL to the playable web build")
    screenshots: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="List of screenshot URLs (max 10)",
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    source_url: str = Field(default="", description="Optional link to source code repository")
    godot_version: str = Field(default="4.4")


class Game(BaseModel):
    id: str
    title: str
    description: str
    web_url: str
    screenshots: list[str]
    tags: list[str]
    source_url: str
    godot_version: str
    author_id: str
    author_name: str
    average_rating: float
    rating_count: int
    play_count: int
    published_at: str
    updated_at: str


class GameListResponse(BaseModel):
    games: list[Game]
    total: int
    page: int
    page_size: int


class RateGameRequest(BaseModel):
    score: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    review: str = Field(default="", max_length=2048, description="Optional text review")


class Rating(BaseModel):
    id: str
    game_id: str
    user_id: str
    score: int
    review: str
    created_at: str


class RateGameResponse(BaseModel):
    rating: Rating
    new_average: float
    total_ratings: int


class JamStatus(str, Enum):
    upcoming = "upcoming"
    active = "active"
    voting = "voting"
    completed = "completed"


class CreateGameJamRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=4096)
    theme: str = Field(default="", max_length=256, description="Jam theme (can be revealed at start)")
    start_date: str = Field(..., description="ISO 8601 date when the jam begins")
    end_date: str = Field(..., description="ISO 8601 date when submissions close")
    voting_end_date: str = Field(default="", description="ISO 8601 date when voting ends")
    max_participants: int = Field(default=0, ge=0, description="0 = unlimited")
    rules: list[str] = Field(default_factory=list)


class GameJam(BaseModel):
    id: str
    title: str
    description: str
    theme: str
    start_date: str
    end_date: str
    voting_end_date: str
    max_participants: int
    rules: list[str]
    status: JamStatus
    organizer_id: str
    participant_count: int
    entry_count: int
    created_at: str


class JamEntry(BaseModel):
    id: str
    jam_id: str
    game_id: str
    participant_id: str
    submitted_at: str


class JoinJamResponse(BaseModel):
    jam_id: str
    message: str


class SubmitJamEntryRequest(BaseModel):
    game_id: str = Field(..., description="ID of the published game to submit")


class SubmitJamEntryResponse(BaseModel):
    entry: JamEntry
    message: str


# ---------------------------------------------------------------------------
# Game Publishing Endpoints
# ---------------------------------------------------------------------------


@router.post("/games", response_model=Game, status_code=status.HTTP_201_CREATED)
async def publish_game(
    req: PublishGameRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Publish a game to the community showcase."""
    game_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    game = Game(
        id=game_id,
        title=req.title,
        description=req.description,
        web_url=req.web_url,
        screenshots=req.screenshots,
        tags=req.tags,
        source_url=req.source_url,
        godot_version=req.godot_version,
        author_id=current_user["id"],
        author_name=current_user.get("display_name", current_user.get("username", "")),
        average_rating=0.0,
        rating_count=0,
        play_count=0,
        published_at=now,
        updated_at=now,
    )

    games = _load_json(GAMES_FILE)
    games.append(game.model_dump())
    _save_json(GAMES_FILE, games)

    return game


@router.get("/games", response_model=GameListResponse)
async def browse_games(
    search: str = Query(default="", description="Search in title and description"),
    tag: str = Query(default="", description="Filter by tag"),
    sort: GameSortField = Query(default=GameSortField.newest, description="Sort order"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Browse published games with search, filtering, and pagination."""
    games = _load_json(GAMES_FILE)

    # Filter
    if search:
        search_lower = search.lower()
        games = [
            g for g in games
            if search_lower in g.get("title", "").lower()
            or search_lower in g.get("description", "").lower()
        ]
    if tag:
        games = [g for g in games if tag in g.get("tags", [])]

    # Sort
    if sort == GameSortField.newest:
        games.sort(key=lambda g: g.get("published_at", ""), reverse=True)
    elif sort == GameSortField.top_rated:
        games.sort(key=lambda g: g.get("average_rating", 0), reverse=True)
    elif sort == GameSortField.most_played:
        games.sort(key=lambda g: g.get("play_count", 0), reverse=True)

    total = len(games)
    start = (page - 1) * page_size
    page_games = games[start : start + page_size]

    return GameListResponse(
        games=[Game(**g) for g in page_games],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/games/{game_id}", response_model=Game)
async def get_game(game_id: str):
    """Get details of a published game."""
    games = _load_json(GAMES_FILE)
    for g in games:
        if g["id"] == game_id:
            return Game(**g)
    raise HTTPException(status_code=404, detail="Game not found")


# ---------------------------------------------------------------------------
# Rating Endpoints
# ---------------------------------------------------------------------------


@router.post("/games/{game_id}/rate", response_model=RateGameResponse)
async def rate_game(
    game_id: str,
    req: RateGameRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Rate a published game (1-5 stars with optional review).

    Users can update their rating by submitting again.
    """
    games = _load_json(GAMES_FILE)
    game_index = None
    for i, g in enumerate(games):
        if g["id"] == game_id:
            game_index = i
            break
    if game_index is None:
        raise HTTPException(status_code=404, detail="Game not found")

    # Cannot rate own game
    if games[game_index]["author_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot rate your own game")

    now = datetime.now(timezone.utc).isoformat()
    ratings = _load_json(RATINGS_FILE)

    # Update existing rating or create new one
    existing_index = None
    for i, r in enumerate(ratings):
        if r["game_id"] == game_id and r["user_id"] == current_user["id"]:
            existing_index = i
            break

    rating = Rating(
        id=ratings[existing_index]["id"] if existing_index is not None else uuid.uuid4().hex,
        game_id=game_id,
        user_id=current_user["id"],
        score=req.score,
        review=req.review,
        created_at=now,
    )

    if existing_index is not None:
        ratings[existing_index] = rating.model_dump()
    else:
        ratings.append(rating.model_dump())

    _save_json(RATINGS_FILE, ratings)

    # Recalculate average
    game_ratings = [r for r in ratings if r["game_id"] == game_id]
    total_ratings = len(game_ratings)
    average = sum(r["score"] for r in game_ratings) / total_ratings if total_ratings else 0.0
    average = round(average, 2)

    games[game_index]["average_rating"] = average
    games[game_index]["rating_count"] = total_ratings
    _save_json(GAMES_FILE, games)

    return RateGameResponse(
        rating=rating,
        new_average=average,
        total_ratings=total_ratings,
    )


# ---------------------------------------------------------------------------
# Game Jam Endpoints
# ---------------------------------------------------------------------------


@router.post("/gamejam", response_model=GameJam, status_code=status.HTTP_201_CREATED)
async def create_game_jam(
    req: CreateGameJamRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new game jam event."""
    jam_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    jam = GameJam(
        id=jam_id,
        title=req.title,
        description=req.description,
        theme=req.theme,
        start_date=req.start_date,
        end_date=req.end_date,
        voting_end_date=req.voting_end_date,
        max_participants=req.max_participants,
        rules=req.rules,
        status=JamStatus.upcoming,
        organizer_id=current_user["id"],
        participant_count=0,
        entry_count=0,
        created_at=now,
    )

    jams = _load_json(GAMEJAMS_FILE)
    jams.append(jam.model_dump())
    _save_json(GAMEJAMS_FILE, jams)

    return jam


@router.get("/gamejam", response_model=list[GameJam])
async def list_game_jams(
    status_filter: str = Query(default="", alias="status", description="Filter by status"),
):
    """List all game jams, optionally filtered by status."""
    jams = _load_json(GAMEJAMS_FILE)
    if status_filter:
        jams = [j for j in jams if j.get("status") == status_filter]
    jams.sort(key=lambda j: j.get("start_date", ""), reverse=True)
    return [GameJam(**j) for j in jams]


@router.get("/gamejam/{jam_id}", response_model=GameJam)
async def get_game_jam(jam_id: str):
    """Get details of a game jam."""
    jams = _load_json(GAMEJAMS_FILE)
    for j in jams:
        if j["id"] == jam_id:
            return GameJam(**j)
    raise HTTPException(status_code=404, detail="Game jam not found")


@router.post("/gamejam/{jam_id}/join", response_model=JoinJamResponse)
async def join_game_jam(
    jam_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Join a game jam as a participant."""
    jams = _load_json(GAMEJAMS_FILE)
    jam_index = None
    for i, j in enumerate(jams):
        if j["id"] == jam_id:
            jam_index = i
            break
    if jam_index is None:
        raise HTTPException(status_code=404, detail="Game jam not found")

    jam = jams[jam_index]
    if jam["status"] not in (JamStatus.upcoming, JamStatus.active):
        raise HTTPException(status_code=400, detail="Cannot join a jam that is not upcoming or active")

    if jam["max_participants"] > 0 and jam["participant_count"] >= jam["max_participants"]:
        raise HTTPException(status_code=400, detail="Game jam is full")

    # Check if already joined
    entries = _load_json(JAM_ENTRIES_FILE)
    for e in entries:
        if e["jam_id"] == jam_id and e["participant_id"] == current_user["id"]:
            return JoinJamResponse(jam_id=jam_id, message="Already joined this jam")

    # Increment participant count
    jams[jam_index]["participant_count"] = jam.get("participant_count", 0) + 1
    _save_json(GAMEJAMS_FILE, jams)

    # Create a placeholder entry (game_id will be set on submission)
    entry = JamEntry(
        id=uuid.uuid4().hex,
        jam_id=jam_id,
        game_id="",
        participant_id=current_user["id"],
        submitted_at="",
    )
    entries.append(entry.model_dump())
    _save_json(JAM_ENTRIES_FILE, entries)

    return JoinJamResponse(jam_id=jam_id, message=f"Joined game jam '{jam['title']}'")


@router.post("/gamejam/{jam_id}/submit", response_model=SubmitJamEntryResponse)
async def submit_jam_entry(
    jam_id: str,
    req: SubmitJamEntryRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Submit a game as an entry to a game jam."""
    # Verify jam exists and is active
    jams = _load_json(GAMEJAMS_FILE)
    jam = None
    jam_index = None
    for i, j in enumerate(jams):
        if j["id"] == jam_id:
            jam = j
            jam_index = i
            break
    if jam is None:
        raise HTTPException(status_code=404, detail="Game jam not found")

    if jam["status"] not in (JamStatus.active, JamStatus.upcoming):
        raise HTTPException(status_code=400, detail="Submissions are closed for this jam")

    # Verify game exists
    games = _load_json(GAMES_FILE)
    game = None
    for g in games:
        if g["id"] == req.game_id:
            game = g
            break
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if game["author_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only submit your own games")

    # Find participant entry and update
    entries = _load_json(JAM_ENTRIES_FILE)
    entry_index = None
    for i, e in enumerate(entries):
        if e["jam_id"] == jam_id and e["participant_id"] == current_user["id"]:
            entry_index = i
            break

    now = datetime.now(timezone.utc).isoformat()

    if entry_index is None:
        # Auto-join if not already joined
        entry = JamEntry(
            id=uuid.uuid4().hex,
            jam_id=jam_id,
            game_id=req.game_id,
            participant_id=current_user["id"],
            submitted_at=now,
        )
        entries.append(entry.model_dump())
        jams[jam_index]["participant_count"] = jam.get("participant_count", 0) + 1
    else:
        was_new_submission = entries[entry_index].get("game_id", "") == ""
        entries[entry_index]["game_id"] = req.game_id
        entries[entry_index]["submitted_at"] = now
        entry = JamEntry(**entries[entry_index])

    # Update entry count
    submitted_entries = [
        e for e in entries
        if e["jam_id"] == jam_id and e.get("game_id", "") != ""
    ]
    jams[jam_index]["entry_count"] = len(submitted_entries)

    _save_json(JAM_ENTRIES_FILE, entries)
    _save_json(GAMEJAMS_FILE, jams)

    return SubmitJamEntryResponse(
        entry=entry if entry_index is None else JamEntry(**entries[entry_index]),
        message=f"Game '{game['title']}' submitted to jam '{jam['title']}'",
    )
