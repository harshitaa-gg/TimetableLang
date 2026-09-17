"""
timetable_generator.py
======================

PHASE 3 of the TimetableLang compiler: **timetable generation**.

Where Phase 2 (`semantic_analyzer.py`) answers:

    "Is this program logically valid?"

this module answers:

    "How do we produce the final examination timetable from the valid
     declarations?"

The two responsibilities are kept completely separate. This module does
not re-run the lexer, the parser, or the semantic analyzer, and it does
not build a second symbol table -- it reads the symbol tables that the
`SemanticAnalyzer` already built.

Pipeline position
-----------------

    Lexer -> Parser -> AST -> SemanticAnalyzer -> TimetableGenerator

What the generator decides
--------------------------

Every `exam` declaration in TimetableLang already names the resources it
needs (`room`, `invigilator`, `students`). Those are the exam's
*declared resources* and the generator keeps them exactly as written.

The thing the generator actually decides is the **time slot**:

* `slot 1`, `slot 2`, ...  -> a **fixed** (pinned) slot. The author has
  chosen the slot by hand; the generator honours it and only verifies it.
* `slot 0`                 -> an **AUTO** slot. The author is asking the
  compiler to choose the slot. This is what the generation algorithm
  searches for.

`slot 0` needs **no change to the lexer, the grammar, or the parser**:
the grammar already accepts any non-negative integer after `slot`, and
slot 0 is not a real examination slot (real slots are numbered from 1).

Constraints enforced on every accepted assignment
-------------------------------------------------

1. ROOM        -- a room hosts at most one exam per slot.
2. INVIGILATOR -- an invigilator supervises at most one exam per slot.
3. STUDENT GROUP -- a group sits at most one exam per slot.
4. CAPACITY    -- room capacity >= student group size.
5. DECLARATION -- only declared rooms / invigilators / groups may be used.

Constraints 4 and 5 are already guaranteed by Phase 2, but they are
re-checked here as a safety net so that the generator can never emit an
assignment it has not itself verified.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The slot number that means "let the compiler choose this exam's slot".
AUTO_SLOT = 0

#: Real examination slots are numbered starting from this value.
FIRST_SLOT = 1


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TimetableGenerationError(Exception):
    """
    Raised when no valid timetable can be produced for a program that is
    otherwise lexically, syntactically and semantically valid.

    Carries the course that could not be placed and, where available, the
    per-slot reasons that blocked it, so the message can explain *why*
    generation failed rather than just that it failed.
    """

    def __init__(
        self,
        message: str,
        course: Optional[str] = None,
        reasons: Optional[Sequence[str]] = None,
    ) -> None:
        self.message = message
        self.course = course
        self.reasons: List[str] = list(reasons or [])
        super().__init__(self.__str__())

    def __str__(self) -> str:
        text = f"Timetable Generation Error: {self.message}"
        if self.reasons:
            text += "\n  Blocking reasons:"
            for reason in self.reasons:
                text += f"\n    - {reason}"
        return text


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Assignment:
    """
    One finished row of the generated timetable: a single exam placed in a
    single slot with its declared resources.
    """

    course: str
    room: str
    invigilator: str
    student_group: str
    slot: int
    #: True if the generator chose this slot (the source said `slot 0`),
    #: False if the slot was written explicitly in the source.
    auto_assigned: bool = False

    def __str__(self) -> str:
        return (
            f"{self.course}: room={self.room}, invigilator={self.invigilator}, "
            f"students={self.student_group}, slot={self.slot}"
        )


@dataclass
class ExamRequest:
    """
    An exam declaration reduced to the plain values the generator needs.

    This is deliberately a *flat copy* of the AST node's fields (plus the
    node itself for error locations) so that the generation algorithm never
    has to know the shape of the AST.
    """

    course: str
    room: str
    invigilator: str
    student_group: str
    requested_slot: int
    order: int  # position in the source file, used to keep output stable
    node: Any = None

    @property
    def is_auto(self) -> bool:
        """True if the compiler must choose this exam's slot."""
        return self.requested_slot == AUTO_SLOT


@dataclass
class Timetable:
    """The final result of Phase 3."""

    assignments: List[Assignment]
    slot_count: int

    def slots_used(self) -> List[int]:
        """Sorted list of the slots that actually hold at least one exam."""
        return sorted({a.slot for a in self.assignments})

    def assignments_in_slot(self, slot: int) -> List[Assignment]:
        """All assignments in one slot, ordered by course name."""
        rows = [a for a in self.assignments if a.slot == slot]
        return sorted(rows, key=lambda a: a.course)


# ---------------------------------------------------------------------------
# Small helpers for reading AST nodes / symbol tables tolerantly
# ---------------------------------------------------------------------------


def _first_attr(node: Any, names: Sequence[str], what: str) -> Any:
    """
    Return the first attribute in `names` that exists on `node`.

    The AST field for (say) the student group could reasonably be called
    `students` or `group`; looking for several candidate names keeps this
    module independent of that naming choice.
    """
    for name in names:
        if hasattr(node, name):
            return getattr(node, name)
    raise TimetableGenerationError(
        f"Internal error: could not read the {what} of {type(node).__name__!r}. "
        f"Tried attribute names: {', '.join(names)}."
    )


def _as_name(value: Any) -> str:
    """
    Normalise an AST field to a plain string name.

    Handles the field being a `str` already, or a Token / node wrapper that
    stores the text in `.value`, `.name` or `.lexeme`.
    """
    if isinstance(value, str):
        return value
    for attr in ("value", "name", "lexeme"):
        if hasattr(value, attr):
            inner = getattr(value, attr)
            if isinstance(inner, str):
                return inner
    return str(value)


def _as_int(value: Any, what: str) -> int:
    """Normalise an AST field to a plain int."""
    if isinstance(value, bool):  # guard: bool is a subclass of int
        raise TimetableGenerationError(f"Internal error: {what} is a boolean.")
    if isinstance(value, int):
        return value
    for attr in ("value", "number"):
        if hasattr(value, attr):
            inner = getattr(value, attr)
            if isinstance(inner, int):
                return inner
            if isinstance(inner, str) and inner.isdigit():
                return int(inner)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise TimetableGenerationError(
        f"Internal error: could not read {what} as an integer (got {value!r})."
    )


def _location_suffix(node: Any) -> str:
    """" (line L, column C)" if the AST node carries a location, else ""."""
    line = getattr(node, "line", None)
    column = getattr(node, "column", None)
    if line is None:
        return ""
    if column is None:
        return f" (line {line})"
    return f" (line {line}, column {column})"


# ---------------------------------------------------------------------------
# The generator
# ---------------------------------------------------------------------------


class TimetableGenerator:
    """
    Produces a final examination timetable from a semantically validated
    program.

    Usage
    -----
        analyzer = SemanticAnalyzer(program)
        analyzer.analyze()                     # Phase 2 must run first

        generator = TimetableGenerator(analyzer)
        timetable = generator.generate()       # raises TimetableGenerationError

    The algorithm is a **deterministic sequential assignment with
    backtracking**:

    * exams are handled in source order;
    * candidate slots are tried in ascending order (1, 2, 3, ...);
    * an assignment is accepted only after every constraint has been
      checked against the assignments already made;
    * if an exam has no valid slot left, the algorithm undoes the previous
      exam's choice and tries its next slot instead.

    It is *not* an optimizer. It does not minimise the number of slots, or
    balance load, or score solutions -- it returns the first complete,
    fully valid assignment found in this fixed order, which makes the same
    input always produce the same timetable.
    """

    def __init__(self, analyzer: Any, max_slots: Optional[int] = None) -> None:
        """
        Args:
            analyzer: the `SemanticAnalyzer` that has already successfully
                validated the program. Its symbol tables (`rooms`,
                `invigilators`, `groups`, `exams`) are reused as-is.
            max_slots: how many examination slots are available. If None,
                a sensible default is derived from the program (see
                `_determine_slot_count`).
        """
        self.analyzer = analyzer

        # --- Reuse the Phase 2 symbol tables. No second symbol table. ----
        self.rooms: Dict[str, Any] = self._read_table(analyzer, "rooms")
        self.invigilators: Dict[str, Any] = self._read_table(analyzer, "invigilators")
        self.groups: Dict[str, Any] = self._read_table(analyzer, "groups")
        self.exam_nodes: List[Any] = list(self._read_exams(analyzer))

        self.requested_max_slots = max_slots

        # --- Occupancy tables: slot -> set of resources already used -----
        self._rooms_busy: Dict[int, Set[str]] = {}
        self._invigilators_busy: Dict[int, Set[str]] = {}
        self._groups_busy: Dict[int, Set[str]] = {}

        # --- Result being built ------------------------------------------
        self._assignments: List[Assignment] = []

        # --- Diagnostics for a good failure message ----------------------
        self._deepest_index: int = -1
        self._deepest_reasons: List[str] = []
        self._deepest_course: Optional[str] = None

    # -- reading the symbol tables -------------------------------------

    @staticmethod
    def _read_table(analyzer: Any, name: str) -> Dict[str, Any]:
        table = getattr(analyzer, name, None)
        if table is None:
            raise TimetableGenerationError(
                f"Internal error: the semantic analyzer has no '{name}' symbol "
                f"table. Timetable generation requires Phase 2 to have run."
            )
        return dict(table)

    @staticmethod
    def _read_exams(analyzer: Any) -> Sequence[Any]:
        exams = getattr(analyzer, "exams", None)
        if exams is None:
            raise TimetableGenerationError(
                "Internal error: the semantic analyzer has no 'exams' list. "
                "Timetable generation requires Phase 2 to have run."
            )
        return exams

    # -- step 1: turn AST exam nodes into flat ExamRequests ---------------

    def _collect_requests(self) -> List[ExamRequest]:
        """Read every exam declaration out of the AST / symbol table."""
        requests: List[ExamRequest] = []
        for index, node in enumerate(self.exam_nodes):
            course = _as_name(
                _first_attr(node, ("name", "course", "course_name"), "course name")
            )
            room = _as_name(_first_attr(node, ("room", "room_name"), "room"))
            invigilator = _as_name(
                _first_attr(node, ("invigilator", "invigilator_name"), "invigilator")
            )
            group = _as_name(
                _first_attr(
                    node,
                    ("students", "group", "student_group", "students_name"),
                    "student group",
                )
            )
            slot = _as_int(
                _first_attr(node, ("slot", "slot_number"), "slot"),
                f"the slot of exam '{course}'",
            )
            requests.append(
                ExamRequest(
                    course=course,
                    room=room,
                    invigilator=invigilator,
                    student_group=group,
                    requested_slot=slot,
                    order=index,
                    node=node,
                )
            )
        return requests

    # -- step 2: safety-net validation of the declarations ---------------

    def _check_declared(self, request: ExamRequest) -> None:
        """
        DECLARATION CONSTRAINT: only declared resources may be scheduled.

        Phase 2 already guarantees this; re-checking means the generator
        never relies on an assumption it has not verified itself.
        """
        where = _location_suffix(request.node)
        if request.room not in self.rooms:
            raise TimetableGenerationError(
                f"Exam '{request.course}' uses undeclared room "
                f"'{request.room}'{where}.",
                course=request.course,
            )
        if request.invigilator not in self.invigilators:
            raise TimetableGenerationError(
                f"Exam '{request.course}' uses undeclared invigilator "
                f"'{request.invigilator}'{where}.",
                course=request.course,
            )
        if request.student_group not in self.groups:
            raise TimetableGenerationError(
                f"Exam '{request.course}' uses undeclared student group "
                f"'{request.student_group}'{where}.",
                course=request.course,
            )

    def _room_capacity(self, room_name: str) -> int:
        return _as_int(
            _first_attr(self.rooms[room_name], ("capacity",), "room capacity"),
            f"the capacity of room '{room_name}'",
        )

    def _group_size(self, group_name: str) -> int:
        return _as_int(
            _first_attr(self.groups[group_name], ("size",), "group size"),
            f"the size of group '{group_name}'",
        )

    def _check_capacity(self, request: ExamRequest) -> None:
        """CAPACITY CONSTRAINT: room capacity must cover the group size."""
        capacity = self._room_capacity(request.room)
        size = self._group_size(request.student_group)
        if size > capacity:
            raise TimetableGenerationError(
                f"Exam '{request.course}' cannot be scheduled: room "
                f"'{request.room}' holds {capacity} students but group "
                f"'{request.student_group}' has {size}"
                f"{_location_suffix(request.node)}.",
                course=request.course,
            )

    # -- step 3: how many slots are available ----------------------------

    def _determine_slot_count(self, requests: Sequence[ExamRequest]) -> int:
        """
        Decide how many examination slots the generator may use.

        Order of preference:

        1. an explicit `max_slots` passed in by the caller (the
           `--max-slots N` command-line option);
        2. otherwise, enough slots that a solution is always possible in
           principle: the number of exams, but never fewer than the
           highest slot number written explicitly in the source.

        The default of "one slot per exam" is the safe upper bound -- in the
        very worst case every exam clashes with every other one and each
        needs a slot of its own.
        """
        highest_pinned = max(
            (r.requested_slot for r in requests if not r.is_auto), default=0
        )
        if self.requested_max_slots is not None:
            if self.requested_max_slots < 1:
                raise TimetableGenerationError(
                    f"Invalid slot count: {self.requested_max_slots}. "
                    f"At least 1 slot is required."
                )
            if highest_pinned > self.requested_max_slots:
                raise TimetableGenerationError(
                    f"Exam slot {highest_pinned} is written explicitly in the "
                    f"source, but only {self.requested_max_slots} slot(s) are "
                    f"available."
                )
            return self.requested_max_slots
        return max(len(requests), highest_pinned, FIRST_SLOT)

    # -- step 4: the constraint checks used during assignment ------------

    def _blocking_reasons(self, request: ExamRequest, slot: int) -> List[str]:
        """
        Return the reasons (possibly none) why `request` may not occupy
        `slot`, given everything assigned so far.

        An empty list means the slot is acceptable.
        """
        reasons: List[str] = []
        if request.room in self._rooms_busy.get(slot, ()):
            reasons.append(
                f"slot {slot}: room '{request.room}' is already booked by "
                f"'{self._who_uses(self._rooms_busy, slot, request.room, 'room')}'"
            )
        if request.invigilator in self._invigilators_busy.get(slot, ()):
            reasons.append(
                f"slot {slot}: invigilator '{request.invigilator}' is already "
                f"supervising '"
                f"{self._who_uses(self._invigilators_busy, slot, request.invigilator, 'invigilator')}'"
            )
        if request.student_group in self._groups_busy.get(slot, ()):
            reasons.append(
                f"slot {slot}: student group '{request.student_group}' already "
                f"has exam '"
                f"{self._who_uses(self._groups_busy, slot, request.student_group, 'group')}'"
            )
        return reasons

    def _who_uses(
        self, _table: Dict[int, Set[str]], slot: int, resource: str, kind: str
    ) -> str:
        """Find which already-placed course is occupying a resource in a slot."""
        for assignment in self._assignments:
            if assignment.slot != slot:
                continue
            if kind == "room" and assignment.room == resource:
                return assignment.course
            if kind == "invigilator" and assignment.invigilator == resource:
                return assignment.course
            if kind == "group" and assignment.student_group == resource:
                return assignment.course
        return "another exam"

    # -- step 5: place / un-place an exam --------------------------------

    def _place(self, request: ExamRequest, slot: int, auto: bool) -> Assignment:
        """Record an accepted assignment and mark its resources as busy."""
        self._rooms_busy.setdefault(slot, set()).add(request.room)
        self._invigilators_busy.setdefault(slot, set()).add(request.invigilator)
        self._groups_busy.setdefault(slot, set()).add(request.student_group)

        assignment = Assignment(
            course=request.course,
            room=request.room,
            invigilator=request.invigilator,
            student_group=request.student_group,
            slot=slot,
            auto_assigned=auto,
        )
        self._assignments.append(assignment)
        return assignment

    def _unplace(self, request: ExamRequest, slot: int) -> None:
        """Undo `_place` -- used when backtracking."""
        self._rooms_busy.get(slot, set()).discard(request.room)
        self._invigilators_busy.get(slot, set()).discard(request.invigilator)
        self._groups_busy.get(slot, set()).discard(request.student_group)
        self._assignments.pop()

    # -- step 6: the public entry point ----------------------------------

    def generate(self) -> Timetable:
        """
        Build and return the final timetable.

        Raises:
            TimetableGenerationError: if no valid complete timetable exists.
                Nothing partial is ever returned.
        """
        # Reset, so calling generate() twice is safe.
        self._rooms_busy.clear()
        self._invigilators_busy.clear()
        self._groups_busy.clear()
        self._assignments = []
        self._deepest_index = -1
        self._deepest_reasons = []
        self._deepest_course = None

        requests = self._collect_requests()

        if not requests:
            # A program with rooms/invigilators/groups but no exams is valid;
            # its timetable is simply empty.
            return Timetable(assignments=[], slot_count=0)

        # Safety-net checks that do not depend on slot choice.
        for request in requests:
            self._check_declared(request)
            self._check_capacity(request)

        slot_count = self._determine_slot_count(requests)

        # Pinned exams first: their slots are fixed, so placing them before
        # searching gives the auto exams the most accurate picture of what is
        # already busy. Source order is preserved inside each group, which is
        # what makes the result deterministic.
        pinned = [r for r in requests if not r.is_auto]
        auto = [r for r in requests if r.is_auto]

        self._place_pinned(pinned, slot_count)

        if not self._assign_auto(auto, 0, slot_count):
            raise self._build_failure(slot_count)

        ordered = sorted(self._assignments, key=lambda a: (a.slot, a.course))
        return Timetable(assignments=ordered, slot_count=slot_count)

    # -- step 6a: fixed slots --------------------------------------------

    def _place_pinned(self, pinned: Sequence[ExamRequest], slot_count: int) -> None:
        """
        Place every exam that named its own slot.

        Phase 2 has already proved these do not clash with each other, so a
        clash here means the analyzer and the generator disagree -- which is
        reported as an error rather than silently repaired, because repairing
        an explicitly requested slot is not this phase's job.
        """
        for request in pinned:
            slot = request.requested_slot
            if slot < FIRST_SLOT or slot > slot_count:
                raise TimetableGenerationError(
                    f"Exam '{request.course}' requests slot {slot}, which is "
                    f"outside the available range {FIRST_SLOT}..{slot_count}"
                    f"{_location_suffix(request.node)}.",
                    course=request.course,
                )
            reasons = self._blocking_reasons(request, slot)
            if reasons:
                raise TimetableGenerationError(
                    f"Exam '{request.course}' cannot use its requested slot "
                    f"{slot}{_location_suffix(request.node)}.",
                    course=request.course,
                    reasons=reasons,
                )
            self._place(request, slot, auto=False)

    # -- step 6b: the backtracking search --------------------------------

    def _assign_auto(
        self, auto: Sequence[ExamRequest], index: int, slot_count: int
    ) -> bool:
        """
        Assign `auto[index:]` to slots, backtracking on failure.

        Returns True if every remaining exam was placed successfully.

        This is the core of the generation algorithm:

            try slot 1 for this exam
              -> does it break any constraint?
                   yes -> try slot 2, 3, ... up to slot_count
                   no  -> keep it and move on to the next exam
            if no slot works, return False so that the *previous* exam
            gives up its slot and tries the next one instead.
        """
        if index >= len(auto):
            return True  # every exam placed

        request = auto[index]
        reasons_seen: List[str] = []

        for slot in range(FIRST_SLOT, slot_count + 1):
            reasons = self._blocking_reasons(request, slot)
            if reasons:
                reasons_seen.extend(reasons)
                continue

            self._place(request, slot, auto=True)
            if self._assign_auto(auto, index + 1, slot_count):
                return True
            self._unplace(request, slot)  # backtrack and try the next slot

        # Remember the furthest point the search reached: that exam is the
        # most useful one to name in the error message.
        if index > self._deepest_index:
            self._deepest_index = index
            self._deepest_course = request.course
            self._deepest_reasons = reasons_seen
        return False

    def _build_failure(self, slot_count: int) -> TimetableGenerationError:
        """Turn the recorded search diagnostics into a clear error."""
        course = self._deepest_course or "unknown"
        reasons = self._deepest_reasons
        if not reasons:
            reasons = [
                f"no slot in the range {FIRST_SLOT}..{slot_count} was free for "
                f"this exam's declared resources"
            ]
        return TimetableGenerationError(
            f"Could not assign exam '{course}' to any available slot "
            f"({slot_count} slot(s) available).",
            course=course,
            reasons=reasons,
        )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

_HEADER_COURSE = "Course"
_HEADER_GROUP = "Student Group"
_HEADER_ROOM = "Room"
_HEADER_INVIG = "Invigilator"
_HEADER_SLOT = "Slot"


def format_timetable(timetable: Timetable) -> str:
    """
    Render a generated timetable as a readable console table.

    Example::

        ============================================================
        GENERATED EXAMINATION TIMETABLE
        ============================================================

        Course       Student Group   Room      Invigilator   Slot
        ------------------------------------------------------------
        DAA          cse_a           hall_a    prof_x        1
        DBMS         cse_b           hall_b    prof_y        1
        OS           cse_a           hall_a    prof_y        2

        ============================================================
        3 exam(s) scheduled across 2 slot(s).
    """
    line = "=" * 60
    out: List[str] = [line, "GENERATED EXAMINATION TIMETABLE", line, ""]

    if not timetable.assignments:
        out.append("(no exams were declared, so the timetable is empty)")
        out.append("")
        out.append(line)
        return "\n".join(out)

    rows = sorted(timetable.assignments, key=lambda a: (a.slot, a.course))

    # Column widths grow to fit the longest value, with the header as a floor.
    w_course = max(len(_HEADER_COURSE), *(len(a.course) for a in rows)) + 2
    w_group = max(len(_HEADER_GROUP), *(len(a.student_group) for a in rows)) + 2
    w_room = max(len(_HEADER_ROOM), *(len(a.room) for a in rows)) + 2
    w_invig = max(len(_HEADER_INVIG), *(len(a.invigilator) for a in rows)) + 2

    out.append(
        f"{_HEADER_COURSE:<{w_course}}{_HEADER_GROUP:<{w_group}}"
        f"{_HEADER_ROOM:<{w_room}}{_HEADER_INVIG:<{w_invig}}{_HEADER_SLOT}"
    )
    out.append("-" * 60)
    for a in rows:
        out.append(
            f"{a.course:<{w_course}}{a.student_group:<{w_group}}"
            f"{a.room:<{w_room}}{a.invigilator:<{w_invig}}{a.slot}"
        )

    out.append("")
    out.append(line)

    slots_used = timetable.slots_used()
    out.append(
        f"{len(rows)} exam(s) scheduled across {len(slots_used)} slot(s) "
        f"(of {timetable.slot_count} available)."
    )

    auto_count = sum(1 for a in rows if a.auto_assigned)
    fixed_count = len(rows) - auto_count
    out.append(
        f"Slots chosen by the generator: {auto_count}. "
        f"Slots written in the source: {fixed_count}."
    )
    return "\n".join(out)


def format_timetable_by_slot(timetable: Timetable) -> str:
    """
    Alternative view of the same timetable, grouped slot by slot.

    Useful when explaining the result, because the constraints ("one room
    per slot", "one exam per group per slot") are easiest to verify by
    reading a single slot at a time.
    """
    if not timetable.assignments:
        return "(empty timetable)"

    out: List[str] = []
    for slot in timetable.slots_used():
        out.append(f"Slot {slot}:")
        for a in timetable.assignments_in_slot(slot):
            out.append(
                f"  {a.course} -- group {a.student_group} in room {a.room}, "
                f"invigilated by {a.invigilator}"
            )
    return "\n".join(out)


def verify_timetable(
    timetable: Timetable,
    analyzer: Optional[Any] = None,
    max_slots: Optional[int] = None,
) -> List[str]:
    """
    Independently re-check a finished timetable and return a list of
    violations (empty list == valid).

    The generator already guarantees validity; this function exists so that
    the tests, pipeline, and anyone reviewing the project can independently
    confirm the output without trusting the algorithm that produced it.

    Checks performed:
    1. Valid slot bounds (slot >= 1 and slot <= max_slots if provided).
    2. No room double-booking in any slot.
    3. No invigilator double-booking in any slot.
    4. No student group double-booking in any slot.
    5. If `analyzer` is passed:
       - Every exam from the source program is scheduled.
       - Room capacity constraint (room.capacity >= group.size).
       - Resource declaration existence (room, invigilator, group exist).
       - Fixed (pinned) slots match their requested source slot.
    """
    problems: List[str] = []
    seen_rooms: Dict[Tuple[int, str], str] = {}
    seen_invigilators: Dict[Tuple[int, str], str] = {}
    seen_groups: Dict[Tuple[int, str], str] = {}

    assigned_courses = set()

    for a in sorted(timetable.assignments, key=lambda x: (x.slot, x.course)):
        assigned_courses.add(a.course)

        # Slot bounds check
        if a.slot < FIRST_SLOT:
            problems.append(
                f"Exam '{a.course}' has invalid non-positive slot {a.slot}."
            )
        if max_slots is not None and a.slot > max_slots:
            problems.append(
                f"Exam '{a.course}' is placed in slot {a.slot}, exceeding max allowed slots ({max_slots})."
            )

        # Resource clash checks
        for table, resource, label in (
            (seen_rooms, a.room, "Room"),
            (seen_invigilators, a.invigilator, "Invigilator"),
            (seen_groups, a.student_group, "Student group"),
        ):
            key = (a.slot, resource)
            if key in table:
                problems.append(
                    f"{label} '{resource}' is double-booked in slot {a.slot} "
                    f"by '{table[key]}' and '{a.course}'."
                )
            else:
                table[key] = a.course

    # If analyzer is provided, independently verify against the program's declarations
    if analyzer is not None:
        rooms = getattr(analyzer, "rooms", {})
        invigilators = getattr(analyzer, "invigilators", {})
        groups = getattr(analyzer, "groups", {})
        exams = getattr(analyzer, "exams", [])

        # Check all declared exams are present
        for exam in exams:
            if exam.course not in assigned_courses:
                problems.append(f"Declared exam '{exam.course}' is missing from the timetable.")

        # Check assignments against declarations & capacities
        for a in timetable.assignments:
            if a.room not in rooms:
                problems.append(f"Exam '{a.course}' uses undeclared room '{a.room}'.")
            if a.invigilator not in invigilators:
                problems.append(f"Exam '{a.course}' uses undeclared invigilator '{a.invigilator}'.")
            if a.student_group not in groups:
                problems.append(f"Exam '{a.course}' uses undeclared student group '{a.student_group}'.")

            if a.room in rooms and a.student_group in groups:
                cap = _as_int(_first_attr(rooms[a.room], ("capacity",), "capacity"), "capacity")
                size = _as_int(_first_attr(groups[a.student_group], ("size",), "size"), "size")
                if size > cap:
                    problems.append(
                        f"Exam '{a.course}': room '{a.room}' capacity ({cap}) is less than group '{a.student_group}' size ({size})."
                    )

        # Check pinned slots were not altered
        exam_dict = {e.course: e for e in exams}
        for a in timetable.assignments:
            if a.course in exam_dict:
                src_exam = exam_dict[a.course]
                if src_exam.slot != AUTO_SLOT and src_exam.slot != a.slot:
                    problems.append(
                        f"Fixed exam '{a.course}' was moved to slot {a.slot} instead of requested slot {src_exam.slot}."
                    )

    return problems

