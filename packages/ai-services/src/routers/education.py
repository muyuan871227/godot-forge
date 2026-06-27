"""Education system — tutorials, classrooms, assignments, and student progress."""
import json
import os
import random
import string
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
EDUCATION_DATA_DIR = Path(
    os.getenv("GODOTFORGE_EDUCATION_DATA_DIR", "/tmp/godotforge/education")
)
CLASSROOMS_FILE = EDUCATION_DATA_DIR / "classrooms.json"
ASSIGNMENTS_FILE = EDUCATION_DATA_DIR / "assignments.json"
SUBMISSIONS_FILE = EDUCATION_DATA_DIR / "submissions.json"


def _ensure_store() -> None:
    EDUCATION_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in (CLASSROOMS_FILE, ASSIGNMENTS_FILE, SUBMISSIONS_FILE):
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


def _generate_invite_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TutorialStep(BaseModel):
    step_number: int = Field(..., ge=1)
    title: str
    description: str
    instructions: str
    expected_outcome: str
    hints: list[str] = Field(default_factory=list)
    validation_script: str = Field(default="", description="GDScript to validate completion")


class Tutorial(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str = Field(
        default="beginner",
        description="beginner | intermediate | advanced",
    )
    estimated_minutes: int = Field(default=30, ge=5)
    tags: list[str] = Field(default_factory=list)
    steps: list[TutorialStep]
    prerequisites: list[str] = Field(default_factory=list, description="IDs of prerequisite tutorials")


class ClassroomRole(str, Enum):
    teacher = "teacher"
    student = "student"


class ClassroomMember(BaseModel):
    user_id: str
    role: ClassroomRole
    joined_at: str


class Classroom(BaseModel):
    id: str
    name: str
    description: str
    invite_code: str
    teacher_id: str
    members: list[ClassroomMember]
    created_at: str


class AssignmentStatus(str, Enum):
    draft = "draft"
    active = "active"
    closed = "closed"


class Assignment(BaseModel):
    id: str
    classroom_id: str
    title: str
    description: str
    tutorial_id: str = Field(default="", description="Optional linked tutorial")
    requirements: list[str]
    due_date: str = Field(default="", description="ISO date string or empty for no deadline")
    status: AssignmentStatus = AssignmentStatus.active
    max_score: int = Field(default=100, ge=0)
    created_by: str
    created_at: str


class SubmissionStatus(str, Enum):
    submitted = "submitted"
    graded = "graded"
    returned = "returned"


class Submission(BaseModel):
    id: str
    assignment_id: str
    classroom_id: str
    student_id: str
    project_url: str = Field(default="", description="URL or path to the student's project")
    notes: str = Field(default="")
    score: int | None = None
    feedback: str = ""
    status: SubmissionStatus = SubmissionStatus.submitted
    submitted_at: str


class StudentProgress(BaseModel):
    student_id: str
    username: str
    assignments_total: int
    assignments_submitted: int
    assignments_graded: int
    average_score: float | None
    last_activity: str


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class CreateClassroomRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=1024)


class CreateClassroomResponse(BaseModel):
    classroom: Classroom
    message: str


class JoinClassroomRequest(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=16)


class CreateAssignmentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=4096)
    tutorial_id: str = Field(default="")
    requirements: list[str] = Field(default_factory=list)
    due_date: str = Field(default="")
    max_score: int = Field(default=100, ge=0)


class SubmitWorkRequest(BaseModel):
    assignment_id: str
    project_url: str = Field(default="")
    notes: str = Field(default="", max_length=2048)


# ---------------------------------------------------------------------------
# Default Tutorials
# ---------------------------------------------------------------------------

DEFAULT_TUTORIALS: list[Tutorial] = [
    Tutorial(
        id="tutorial-first-game",
        title="Your First Game",
        description=(
            "Learn the fundamentals of GodotForge by building a simple 2D "
            "dodge-the-obstacles game from scratch using AI-assisted workflows."
        ),
        difficulty="beginner",
        estimated_minutes=45,
        tags=["beginner", "2d", "gdscript", "ai-assist"],
        steps=[
            TutorialStep(
                step_number=1,
                title="Create a New Project",
                description="Set up a new GodotForge project using the CLI or Web UI.",
                instructions=(
                    "Open the GodotForge dashboard and click 'New Project'. "
                    "Name it 'MyFirstGame' and select the blank 2D template."
                ),
                expected_outcome="A new Godot 4.x project is created with the default 2D scene.",
                hints=["You can also run: godotforge init MyFirstGame --template blank-2d"],
            ),
            TutorialStep(
                step_number=2,
                title="Design Your Player",
                description="Use AI to generate a player character sprite and movement script.",
                instructions=(
                    "In the AI panel, type: 'Create a simple spaceship sprite and a "
                    "CharacterBody2D script that moves with arrow keys at 300 pixels/sec'. "
                    "Review the generated code and apply it."
                ),
                expected_outcome="A Player node with a sprite and working movement script.",
                hints=[
                    "You can edit the generated script in the built-in editor.",
                    "Try adjusting the speed value in the exported variable.",
                ],
            ),
            TutorialStep(
                step_number=3,
                title="Add Obstacles",
                description="Generate falling obstacles that the player must avoid.",
                instructions=(
                    "Ask the AI: 'Add randomly spawning obstacles that fall from the top "
                    "of the screen. When they hit the player, show game over. Include a "
                    "score counter that increases over time.'"
                ),
                expected_outcome=(
                    "Obstacles spawn and fall; collision detection works; score displays."
                ),
                hints=["Use Area2D nodes for collision detection."],
            ),
            TutorialStep(
                step_number=4,
                title="Polish and Export",
                description="Add a title screen, sound effects, and export the game.",
                instructions=(
                    "Use AI to generate a title screen scene, a background music track, "
                    "and collision sound effects. Then export the game to HTML5."
                ),
                expected_outcome="A complete, playable game with title screen, audio, and web export.",
                hints=["HTML5 exports work great for sharing on itch.io."],
            ),
        ],
    ),
    Tutorial(
        id="tutorial-ai-art",
        title="AI Art Mastery",
        description=(
            "Master GodotForge's AI image generation pipeline to create "
            "professional-quality sprites, tilesets, and UI elements."
        ),
        difficulty="intermediate",
        estimated_minutes=60,
        tags=["intermediate", "art", "ai-generation", "sprites", "tilemap"],
        prerequisites=["tutorial-first-game"],
        steps=[
            TutorialStep(
                step_number=1,
                title="Understanding the Art Pipeline",
                description="Learn how GodotForge's image generation system works.",
                instructions=(
                    "Read through the generation settings panel. Experiment with the "
                    "provider selector (ComfyUI / Replicate / Local) and understand "
                    "how style presets affect output."
                ),
                expected_outcome="You can explain the difference between providers and style modes.",
                hints=["ComfyUI gives the most control; Replicate is easiest to start with."],
            ),
            TutorialStep(
                step_number=2,
                title="Sprite Sheet Generation",
                description="Generate a complete character sprite sheet with walk, idle, and attack animations.",
                instructions=(
                    "Use the asset browser to generate a character sprite sheet. "
                    "Prompt: 'Pixel art warrior character, 32x32, 4-direction walk cycle, "
                    "idle animation, sword attack animation, fantasy RPG style'. "
                    "Configure the grid to 8 columns."
                ),
                expected_outcome="A sprite sheet image properly split into animation frames.",
                hints=["Use the preview to verify frame alignment before importing."],
            ),
            TutorialStep(
                step_number=3,
                title="Tilemap Creation",
                description="Generate a tileset and paint a level with it.",
                instructions=(
                    "Generate a tileset: 'Fantasy dungeon tileset, 16x16, includes floor, "
                    "walls, doors, treasure chests, traps, and decorations'. "
                    "Import it as a TileSet resource and paint a test level."
                ),
                expected_outcome="A TileMap node using your AI-generated tileset.",
                hints=["Enable auto-tiling rules for seamless wall placement."],
            ),
            TutorialStep(
                step_number=4,
                title="UI Design with AI",
                description="Create a cohesive game UI using AI-generated elements.",
                instructions=(
                    "Generate UI components: buttons, health bars, inventory slots, and "
                    "dialog boxes in a consistent pixel art style. Assemble them into "
                    "a functional HUD scene."
                ),
                expected_outcome="A reusable HUD scene with AI-generated UI theme.",
                hints=["Use Godot's Theme resource to apply consistent styling."],
            ),
        ],
    ),
    Tutorial(
        id="tutorial-complete-rpg",
        title="Building a Complete RPG",
        description=(
            "A comprehensive guide to building a top-down RPG with AI-generated "
            "assets, NPC dialogue, combat system, and inventory management."
        ),
        difficulty="advanced",
        estimated_minutes=180,
        tags=["advanced", "rpg", "2d", "npc-ai", "combat", "inventory"],
        prerequisites=["tutorial-first-game", "tutorial-ai-art"],
        steps=[
            TutorialStep(
                step_number=1,
                title="World Design",
                description="Plan and generate the RPG world map with multiple areas.",
                instructions=(
                    "Use the AI to design a world with 4 zones: village, forest, cave, "
                    "and castle. Generate tilesets for each zone and create the "
                    "base TileMap layouts."
                ),
                expected_outcome="Four interconnected zone scenes with AI-generated tilesets.",
                hints=["Use scene transitions with fade effects between zones."],
            ),
            TutorialStep(
                step_number=2,
                title="Character System",
                description="Build a player character with stats, leveling, and equipment.",
                instructions=(
                    "Ask the AI to generate: a CharacterBody2D player with RPG stats "
                    "(HP, MP, STR, DEF, SPD), an experience/leveling system, and an "
                    "equipment system with weapon/armor slots."
                ),
                expected_outcome="A player character with working stats, level-ups, and equipment.",
                hints=["Store character data in a Resource for easy saving/loading."],
            ),
            TutorialStep(
                step_number=3,
                title="NPC Dialogue System",
                description="Create interactive NPCs with AI-powered dynamic dialogue.",
                instructions=(
                    "Set up the NPC AI system. Create a shopkeeper, a quest giver, and "
                    "a mysterious sage. Use the /npcai/dialogue endpoint for dynamic "
                    "conversations that react to game state."
                ),
                expected_outcome="Three NPCs with unique personalities and context-aware dialogue.",
                hints=[
                    "Pass game_context to the dialogue API for state-aware responses.",
                    "Use the behavior tree generator for NPC movement patterns.",
                ],
            ),
            TutorialStep(
                step_number=4,
                title="Combat System",
                description="Implement a turn-based or real-time combat system.",
                instructions=(
                    "Use AI to generate a turn-based combat system with: attack, "
                    "defend, magic, and item commands. Add enemy AI with different "
                    "strategies. Generate battle UI and victory/defeat screens."
                ),
                expected_outcome="A complete battle system with enemy AI and UI.",
                hints=["Use a state machine for battle flow control."],
            ),
            TutorialStep(
                step_number=5,
                title="Inventory and Quests",
                description="Add inventory management and a quest tracking system.",
                instructions=(
                    "Generate an inventory UI with drag-and-drop, item tooltips, and "
                    "categories. Create a quest log system that tracks objectives and "
                    "rewards. Wire NPCs to give and complete quests."
                ),
                expected_outcome="Working inventory and quest systems integrated with NPCs.",
                hints=["Use Godot signals to track quest objective completion."],
            ),
            TutorialStep(
                step_number=6,
                title="Audio and Polish",
                description="Add music, sound effects, and final polish.",
                instructions=(
                    "Generate background music for each zone using the audio pipeline. "
                    "Add combat sound effects, UI click sounds, and ambient audio. "
                    "Create a save/load system and a title screen with 'New Game' / "
                    "'Continue' options."
                ),
                expected_outcome="A complete, polished RPG with audio, saving, and title screen.",
                hints=["Test the full game loop: new game -> play -> save -> load -> continue."],
            ),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Tutorial Endpoints
# ---------------------------------------------------------------------------


@router.get("/tutorials", response_model=list[Tutorial])
async def list_tutorials(
    difficulty: str = Query(default="", description="Filter by difficulty: beginner, intermediate, advanced"),
    tag: str = Query(default="", description="Filter by tag"),
):
    """List all available tutorials, optionally filtered by difficulty or tag."""
    tutorials = DEFAULT_TUTORIALS
    if difficulty:
        tutorials = [t for t in tutorials if t.difficulty == difficulty]
    if tag:
        tutorials = [t for t in tutorials if tag in t.tags]
    return tutorials


@router.get("/tutorials/{tutorial_id}", response_model=Tutorial)
async def get_tutorial(tutorial_id: str):
    """Get a tutorial with all its steps."""
    for t in DEFAULT_TUTORIALS:
        if t.id == tutorial_id:
            return t
    raise HTTPException(status_code=404, detail="Tutorial not found")


# ---------------------------------------------------------------------------
# Classroom Endpoints
# ---------------------------------------------------------------------------


@router.post("/classroom", response_model=CreateClassroomResponse, status_code=status.HTTP_201_CREATED)
async def create_classroom(
    req: CreateClassroomRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new classroom (teacher only).

    Generates a unique invite code that students can use to join.
    """
    classroom_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    invite_code = _generate_invite_code()

    classroom = Classroom(
        id=classroom_id,
        name=req.name,
        description=req.description,
        invite_code=invite_code,
        teacher_id=current_user["id"],
        members=[
            ClassroomMember(
                user_id=current_user["id"],
                role=ClassroomRole.teacher,
                joined_at=now,
            )
        ],
        created_at=now,
    )

    classrooms = _load_json(CLASSROOMS_FILE)
    classrooms.append(classroom.model_dump())
    _save_json(CLASSROOMS_FILE, classrooms)

    return CreateClassroomResponse(
        classroom=classroom,
        message=f"Classroom created. Share invite code: {invite_code}",
    )


@router.get("/classroom", response_model=list[Classroom])
async def list_classrooms(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List classrooms the current user belongs to."""
    classrooms = _load_json(CLASSROOMS_FILE)
    user_id = current_user["id"]
    result = []
    for c in classrooms:
        for member in c.get("members", []):
            if member.get("user_id") == user_id:
                result.append(Classroom(**c))
                break
    return result


@router.get("/classroom/{classroom_id}", response_model=Classroom)
async def get_classroom(
    classroom_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get classroom details (members only)."""
    classrooms = _load_json(CLASSROOMS_FILE)
    for c in classrooms:
        if c["id"] == classroom_id:
            member_ids = [m["user_id"] for m in c.get("members", [])]
            if current_user["id"] not in member_ids:
                raise HTTPException(status_code=403, detail="Not a member of this classroom")
            return Classroom(**c)
    raise HTTPException(status_code=404, detail="Classroom not found")


@router.post("/classroom/{classroom_id}/join", status_code=status.HTTP_200_OK)
async def join_classroom(
    classroom_id: str,
    req: JoinClassroomRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Join a classroom using an invite code (student)."""
    classrooms = _load_json(CLASSROOMS_FILE)
    for c in classrooms:
        if c["id"] == classroom_id:
            if c["invite_code"] != req.invite_code:
                raise HTTPException(status_code=403, detail="Invalid invite code")

            member_ids = [m["user_id"] for m in c.get("members", [])]
            if current_user["id"] in member_ids:
                return {"message": "Already a member of this classroom"}

            now = datetime.now(timezone.utc).isoformat()
            c["members"].append(
                ClassroomMember(
                    user_id=current_user["id"],
                    role=ClassroomRole.student,
                    joined_at=now,
                ).model_dump()
            )
            _save_json(CLASSROOMS_FILE, classrooms)
            return {"message": f"Joined classroom '{c['name']}' as student"}

    raise HTTPException(status_code=404, detail="Classroom not found")


# ---------------------------------------------------------------------------
# Assignment Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/classroom/{classroom_id}/assignments",
    response_model=Assignment,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    classroom_id: str,
    req: CreateAssignmentRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new assignment for a classroom (teacher only)."""
    classrooms = _load_json(CLASSROOMS_FILE)
    classroom = None
    for c in classrooms:
        if c["id"] == classroom_id:
            classroom = c
            break
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    if classroom["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the teacher can create assignments")

    assignment_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    assignment = Assignment(
        id=assignment_id,
        classroom_id=classroom_id,
        title=req.title,
        description=req.description,
        tutorial_id=req.tutorial_id,
        requirements=req.requirements,
        due_date=req.due_date,
        max_score=req.max_score,
        created_by=current_user["id"],
        created_at=now,
    )

    assignments = _load_json(ASSIGNMENTS_FILE)
    assignments.append(assignment.model_dump())
    _save_json(ASSIGNMENTS_FILE, assignments)

    return assignment


@router.get("/classroom/{classroom_id}/assignments", response_model=list[Assignment])
async def list_assignments(
    classroom_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all assignments for a classroom."""
    assignments = _load_json(ASSIGNMENTS_FILE)
    return [Assignment(**a) for a in assignments if a["classroom_id"] == classroom_id]


# ---------------------------------------------------------------------------
# Progress Endpoint
# ---------------------------------------------------------------------------


@router.get("/classroom/{classroom_id}/progress", response_model=list[StudentProgress])
async def view_progress(
    classroom_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """View student progress across all assignments in a classroom.

    Teachers see all students; students see only their own progress.
    """
    classrooms = _load_json(CLASSROOMS_FILE)
    classroom = None
    for c in classrooms:
        if c["id"] == classroom_id:
            classroom = c
            break
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")

    is_teacher = classroom["teacher_id"] == current_user["id"]
    assignments = [a for a in _load_json(ASSIGNMENTS_FILE) if a["classroom_id"] == classroom_id]
    submissions = [s for s in _load_json(SUBMISSIONS_FILE) if s["classroom_id"] == classroom_id]
    total_assignments = len(assignments)

    students = [
        m for m in classroom.get("members", [])
        if m["role"] == ClassroomRole.student
        or (not is_teacher and m["user_id"] == current_user["id"])
    ]

    if not is_teacher:
        students = [m for m in students if m["user_id"] == current_user["id"]]

    progress_list: list[StudentProgress] = []
    for member in students:
        sid = member["user_id"]
        student_subs = [s for s in submissions if s["student_id"] == sid]
        graded = [s for s in student_subs if s.get("status") == SubmissionStatus.graded]
        scores = [s["score"] for s in graded if s.get("score") is not None]
        avg_score = sum(scores) / len(scores) if scores else None
        last_activity = max(
            (s["submitted_at"] for s in student_subs),
            default=member.get("joined_at", ""),
        )

        progress_list.append(
            StudentProgress(
                student_id=sid,
                username=sid[:8],  # In production, resolve via user service
                assignments_total=total_assignments,
                assignments_submitted=len(student_subs),
                assignments_graded=len(graded),
                average_score=avg_score,
                last_activity=last_activity,
            )
        )

    return progress_list


# ---------------------------------------------------------------------------
# Submission Endpoints
# ---------------------------------------------------------------------------


@router.post("/classroom/{classroom_id}/submit", response_model=Submission, status_code=status.HTTP_201_CREATED)
async def submit_work(
    classroom_id: str,
    req: SubmitWorkRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Submit work for an assignment (student)."""
    # Verify classroom membership
    classrooms = _load_json(CLASSROOMS_FILE)
    classroom = None
    for c in classrooms:
        if c["id"] == classroom_id:
            classroom = c
            break
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")

    member_ids = [m["user_id"] for m in classroom.get("members", [])]
    if current_user["id"] not in member_ids:
        raise HTTPException(status_code=403, detail="Not a member of this classroom")

    # Verify assignment exists
    assignments = _load_json(ASSIGNMENTS_FILE)
    assignment = None
    for a in assignments:
        if a["id"] == req.assignment_id and a["classroom_id"] == classroom_id:
            assignment = a
            break
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found in this classroom")

    submission_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    submission = Submission(
        id=submission_id,
        assignment_id=req.assignment_id,
        classroom_id=classroom_id,
        student_id=current_user["id"],
        project_url=req.project_url,
        notes=req.notes,
        submitted_at=now,
    )

    submissions = _load_json(SUBMISSIONS_FILE)
    submissions.append(submission.model_dump())
    _save_json(SUBMISSIONS_FILE, submissions)

    return submission
