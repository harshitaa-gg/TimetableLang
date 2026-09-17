"""
semantic_analyzer.py
=====================

The Semantic Analyzer for TimetableLang — PHASE 2.

Responsibility: given a syntactically valid AST (produced by
src/parser.py), decide whether the program is LOGICALLY meaningful:

    - Are there duplicate room / invigilator / group declarations?
    - Does every exam reference a room, invigilator, and student
      group that was actually declared?
    - Does the assigned room have enough capacity for the assigned
      student group?
    - Is any room, invigilator, or student group double-booked in
      the same time slot?

This is the THIRD phase of the compiler pipeline:

    Source Code -> Lexer -> Tokens -> Parser -> AST -> [SEMANTIC ANALYZER]

The semantic analyzer works ENTIRELY on the AST. It never looks at
raw source text or tokens directly — that separation is what keeps
"is it structurally valid?" (syntax) cleanly separate from "is it
logically valid?" (semantics).

Symbol tables (rooms, invigilators, groups) are implemented as plain
Python dictionaries, exactly as recommended for this academic
project — no databases, no extra frameworks.

Timetable generation (Phase 3) is NOT performed here. This module
only validates; it does not produce a final schedule.
"""

from .ast_nodes import (
    RoomDeclaration,
    InvigilatorDeclaration,
    GroupDeclaration,
    ExamDeclaration,
)


class SemanticAnalysisError(Exception):
    """
    Raised when a syntactically valid AST fails a semantic check.

    Attributes:
        category: a short label for the kind of semantic error, e.g.
            "Duplicate Declaration", "Undeclared Reference",
            "Capacity Violation", "Room Conflict",
            "Invigilator Conflict", "Group Conflict".
        line, column: source location, when available (taken from the
            AST node that triggered the error).
    """

    def __init__(self, message: str, category: str, line=None, column=None):
        self.category = category
        self.line = line
        self.column = column

        if line is not None and column is not None:
            location = f" (line {line}, column {column})"
        elif line is not None:
            location = f" (line {line})"
        else:
            location = ""

        super().__init__(f"Semantic Error [{category}]{location}: {message}")


class SemanticAnalyzer:
    """
    Walks a Program AST and validates it.

    Usage:
        analyzer = SemanticAnalyzer(program)
        analyzer.analyze()   # raises SemanticAnalysisError on the
                              # first problem found

    After a successful analyze() call, the symbol tables built along
    the way remain available as instance attributes for inspection or
    display:

        analyzer.rooms          # dict: name -> RoomDeclaration
        analyzer.invigilators   # dict: name -> InvigilatorDeclaration
        analyzer.groups         # dict: name -> GroupDeclaration
        analyzer.exams          # list: ExamDeclaration, in source order
    """

    def __init__(self, program):
        self.program = program

        # --- Symbol tables (Section 5/6: "Do not over-engineer") -------
        # Plain dictionaries, keyed by declared name.
        self.rooms = {}          # name -> RoomDeclaration
        self.invigilators = {}   # name -> InvigilatorDeclaration
        self.groups = {}         # name -> GroupDeclaration
        self.exams = []          # ExamDeclaration objects, in order

        # --- Bookings used for conflict detection -----------------------
        # Each maps (resource_name, slot) -> the course that booked it,
        # so conflict messages can be built without re-scanning exams.
        self._room_bookings = {}         # (room_name, slot) -> course
        self._invigilator_bookings = {}  # (invigilator_name, slot) -> course
        self._group_bookings = {}        # (group_name, slot) -> course

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze(self):
        """
        Runs the full Phase 2 semantic analysis pipeline:

            1. build_symbol_tables()  (also detects duplicate
               room/invigilator/group declarations as they occur)
            2. For every exam, in source order:
                 - check_references()
                 - check_room_capacity()
                 - check_room_conflict()
                 - check_invigilator_conflict()
                 - check_group_conflict()

        Raises:
            SemanticAnalysisError: on the first semantic problem found.
        """
        self._build_symbol_tables()

        for exam in self.exams:
            self._check_references(exam)
            self._check_room_capacity(exam)
            self._check_room_conflict(exam)
            self._check_invigilator_conflict(exam)
            self._check_group_conflict(exam)

    # ------------------------------------------------------------------
    # Step 1: Symbol table construction + duplicate-declaration checks
    # ------------------------------------------------------------------

    def _build_symbol_tables(self):
        """
        Walks the top-level declarations in the AST once, in source
        order, and populates the symbol tables. Duplicate room,
        invigilator, or group declarations are reported here, at the
        point where the SECOND (redeclaring) declaration is seen.
        """
        for decl in self.program.declarations:
            if isinstance(decl, RoomDeclaration):
                self._declare_room(decl)
            elif isinstance(decl, InvigilatorDeclaration):
                self._declare_invigilator(decl)
            elif isinstance(decl, GroupDeclaration):
                self._declare_group(decl)
            elif isinstance(decl, ExamDeclaration):
                # Exams are validated later, once every room,
                # invigilator, and group has been fully collected.
                self.exams.append(decl)

    def _declare_room(self, decl: RoomDeclaration):
        if decl.name in self.rooms:
            raise SemanticAnalysisError(
                f"Room '{decl.name}' is already declared.",
                category="Duplicate Declaration",
                line=decl.line,
                column=decl.column,
            )
        self.rooms[decl.name] = decl

    def _declare_invigilator(self, decl: InvigilatorDeclaration):
        if decl.name in self.invigilators:
            raise SemanticAnalysisError(
                f"Invigilator '{decl.name}' is already declared.",
                category="Duplicate Declaration",
                line=decl.line,
                column=decl.column,
            )
        self.invigilators[decl.name] = decl

    def _declare_group(self, decl: GroupDeclaration):
        if decl.name in self.groups:
            raise SemanticAnalysisError(
                f"Group '{decl.name}' is already declared.",
                category="Duplicate Declaration",
                line=decl.line,
                column=decl.column,
            )
        self.groups[decl.name] = decl

    # ------------------------------------------------------------------
    # Step 2a: Reference checks (Checks 4, 5, 6)
    # ------------------------------------------------------------------

    def _check_references(self, exam: ExamDeclaration):
        """Every exam must reference a room, invigilator, and student
        group that were actually declared somewhere in the program."""

        if exam.room not in self.rooms:
            raise SemanticAnalysisError(
                f"Room '{exam.room}' is not declared.",
                category="Undeclared Reference",
                line=exam.line,
                column=exam.column,
            )

        if exam.invigilator not in self.invigilators:
            raise SemanticAnalysisError(
                f"Invigilator '{exam.invigilator}' is not declared.",
                category="Undeclared Reference",
                line=exam.line,
                column=exam.column,
            )

        if exam.students not in self.groups:
            raise SemanticAnalysisError(
                f"Student group '{exam.students}' is not declared.",
                category="Undeclared Reference",
                line=exam.line,
                column=exam.column,
            )

    # ------------------------------------------------------------------
    # Step 2b: Capacity check (Check 7)
    # ------------------------------------------------------------------

    def _check_room_capacity(self, exam: ExamDeclaration):
        """The assigned room must be large enough for the assigned
        student group. Only runs once references are known to be
        valid (see analyze(): _check_references runs first)."""

        room = self.rooms[exam.room]
        group = self.groups[exam.students]

        if group.size > room.capacity:
            raise SemanticAnalysisError(
                f"Room '{room.name}' has capacity {room.capacity}, "
                f"but group '{group.name}' has {group.size} students.",
                category="Capacity Violation",
                line=exam.line,
                column=exam.column,
            )

    # ------------------------------------------------------------------
    # Step 2c: Conflict checks (Checks 8, 9, 10)
    # ------------------------------------------------------------------

    def _check_room_conflict(self, exam: ExamDeclaration):
        """No room may be used by two exams in the same slot."""
        key = (exam.room, exam.slot)
        if key in self._room_bookings:
            raise SemanticAnalysisError(
                f"Room '{exam.room}' is already booked in slot {exam.slot}.",
                category="Room Conflict",
                line=exam.line,
                column=exam.column,
            )
        self._room_bookings[key] = exam.course

    def _check_invigilator_conflict(self, exam: ExamDeclaration):
        """No invigilator may supervise two exams in the same slot."""
        key = (exam.invigilator, exam.slot)
        if key in self._invigilator_bookings:
            raise SemanticAnalysisError(
                f"Invigilator '{exam.invigilator}' is already assigned "
                f"in slot {exam.slot}.",
                category="Invigilator Conflict",
                line=exam.line,
                column=exam.column,
            )
        self._invigilator_bookings[key] = exam.course

    def _check_group_conflict(self, exam: ExamDeclaration):
        """No student group may have two exams in the same slot."""
        key = (exam.students, exam.slot)
        if key in self._group_bookings:
            raise SemanticAnalysisError(
                f"Student group '{exam.students}' already has an exam "
                f"in slot {exam.slot}.",
                category="Group Conflict",
                line=exam.line,
                column=exam.column,
            )
        self._group_bookings[key] = exam.course


# ----------------------------------------------------------------------
# Display helper
# ----------------------------------------------------------------------
#
# Purely a console convenience so the symbol tables can be shown during
# a demo/viva, similar in spirit to ast_nodes.format_ast(). Not part of
# the semantic analysis logic itself.

def format_symbol_tables(analyzer: SemanticAnalyzer) -> str:
    """Render the analyzer's symbol tables as readable text."""

    lines = []

    lines.append("Rooms:")
    if analyzer.rooms:
        for name, room in analyzer.rooms.items():
            lines.append(f"  {name} -> capacity {room.capacity}")
    else:
        lines.append("  (none declared)")

    lines.append("Invigilators:")
    if analyzer.invigilators:
        for name in analyzer.invigilators:
            lines.append(f"  {name}")
    else:
        lines.append("  (none declared)")

    lines.append("Student Groups:")
    if analyzer.groups:
        for name, group in analyzer.groups.items():
            lines.append(f"  {name} -> size {group.size}")
    else:
        lines.append("  (none declared)")

    lines.append("Exams:")
    if analyzer.exams:
        for exam in analyzer.exams:
            lines.append(
                f"  {exam.course}: room={exam.room}, "
                f"invigilator={exam.invigilator}, students={exam.students}, "
                f"slot={exam.slot}"
            )
    else:
        lines.append("  (none declared)")

    return "\n".join(lines)
