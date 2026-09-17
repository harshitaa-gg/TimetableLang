"""
semantic_analyzer.py
====================

The Semantic Analyzer for TimetableLang — PHASE 2.

Responsibility: given a syntactically valid AST (produced by
src/parser.py), decide whether the program is LOGICALLY meaningful:

    - Are there duplicate room / invigilator / group declarations?
    - Does every exam reference a room, invigilator, and student
      group that was actually declared?
    - Does the assigned room have enough capacity for the assigned
      student group?
    - Is any room, invigilator, or student group double-booked
      in the same time slot?

PHASE 3 EXTENSION:
    - slot 0 means the exam is unassigned (AUTO slot).
    - Phase 3 timetable generation will choose its actual slot.

This module performs semantic validation.
"""

from .ast_nodes import (
    RoomDeclaration,
    InvigilatorDeclaration,
    GroupDeclaration,
    ExamDeclaration,
)


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

#: slot 0 means "let the Phase 3 generator choose this exam's slot".
#: Real examination slots are numbered starting from 1.
AUTO_SLOT = 0


# ----------------------------------------------------------------------
# Semantic Analysis Error
# ----------------------------------------------------------------------

class SemanticAnalysisError(Exception):
    """
    Raised when a syntactically valid AST fails a semantic check.

    Attributes:
        category: short label describing the type of semantic error.
        line: source line where the error occurred.
        column: source column where the error occurred.
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

        super().__init__(
            f"Semantic Error [{category}]{location}: {message}"
        )


# ----------------------------------------------------------------------
# Semantic Analyzer
# ----------------------------------------------------------------------

class SemanticAnalyzer:
    """
    Walks a Program AST and validates it.

    Usage:
        analyzer = SemanticAnalyzer(program)
        analyzer.analyze()

    After successful analysis, the following symbol tables remain
    available:

        analyzer.rooms
        analyzer.invigilators
        analyzer.groups
        analyzer.exams
    """

    def __init__(self, program):
        self.program = program

        # --------------------------------------------------------------
        # Symbol tables
        # --------------------------------------------------------------

        self.rooms = {}
        self.invigilators = {}
        self.groups = {}
        self.exams = []

        # --------------------------------------------------------------
        # Bookings used for conflict detection
        #
        # Each dictionary maps:
        #
        #     (resource_name, slot) -> course
        #
        # Example:
        #
        #     ("hall_a", 1) -> "CS101"
        #
        # --------------------------------------------------------------

        self._room_bookings = {}
        self._invigilator_bookings = {}
        self._group_bookings = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze(self):
        """
        Runs the complete semantic analysis pipeline.

        Steps:

            1. Build symbol tables.
            2. Check every exam's references.
            3. Check room capacity.
            4. Check room conflicts.
            5. Check invigilator conflicts.
            6. Check student-group conflicts.

        IMPORTANT FOR PHASE 3:

            If an exam has slot 0 (AUTO slot), the exam is not yet assigned
            to a real timetable slot.

            Therefore:
                - reference checks still run
                - capacity checks still run
                - conflict checks are skipped for slot 0

            The Phase 3 timetable generator will later choose
            a real slot and enforce those conflicts.
        """

        # Step 1:
        # Build rooms, invigilators, groups and exam list.
        self._build_symbol_tables()

        # Step 2:
        # Validate every exam.
        for exam in self.exams:

            # These checks are independent of the exam's slot.
            # They must also run for slot 0.
            self._check_references(exam)
            self._check_room_capacity(exam)

            # ----------------------------------------------------------
            # PHASE 3:
            #
            # slot 0 means the exam is currently unassigned (AUTO).
            #
            # It therefore cannot have a room/invigilator/group
            # conflict yet because it does not occupy a real slot.
            #
            # The timetable generator will choose a real slot later.
            # ----------------------------------------------------------

            if exam.slot == AUTO_SLOT:
                continue

            # Fixed-slot exams are checked normally.
            self._check_room_conflict(exam)
            self._check_invigilator_conflict(exam)
            self._check_group_conflict(exam)

    # ------------------------------------------------------------------
    # Step 1:
    # Symbol table construction + duplicate declaration checks
    # ------------------------------------------------------------------

    def _build_symbol_tables(self):
        """
        Walk through all top-level declarations and populate
        the symbol tables.

        Duplicate room, invigilator and group declarations are
        detected here.
        """

        for decl in self.program.declarations:

            if isinstance(decl, RoomDeclaration):
                self._declare_room(decl)

            elif isinstance(decl, InvigilatorDeclaration):
                self._declare_invigilator(decl)

            elif isinstance(decl, GroupDeclaration):
                self._declare_group(decl)

            elif isinstance(decl, ExamDeclaration):
                # Exams are validated later after all resources
                # have been collected.
                self.exams.append(decl)

    # ------------------------------------------------------------------
    # Room declaration
    # ------------------------------------------------------------------

    def _declare_room(self, decl: RoomDeclaration):
        """
        Add a room to the symbol table.

        Raises an error if the room was already declared.
        """

        if decl.name in self.rooms:
            raise SemanticAnalysisError(
                f"Room '{decl.name}' is already declared.",
                category="Duplicate Declaration",
                line=decl.line,
                column=decl.column,
            )

        self.rooms[decl.name] = decl

    # ------------------------------------------------------------------
    # Invigilator declaration
    # ------------------------------------------------------------------

    def _declare_invigilator(self, decl: InvigilatorDeclaration):
        """
        Add an invigilator to the symbol table.

        Raises an error if the invigilator was already declared.
        """

        if decl.name in self.invigilators:
            raise SemanticAnalysisError(
                f"Invigilator '{decl.name}' is already declared.",
                category="Duplicate Declaration",
                line=decl.line,
                column=decl.column,
            )

        self.invigilators[decl.name] = decl

    # ------------------------------------------------------------------
    # Student group declaration
    # ------------------------------------------------------------------

    def _declare_group(self, decl: GroupDeclaration):
        """
        Add a student group to the symbol table.

        Raises an error if the group was already declared.
        """

        if decl.name in self.groups:
            raise SemanticAnalysisError(
                f"Student group '{decl.name}' is already declared.",
                category="Duplicate Declaration",
                line=decl.line,
                column=decl.column,
            )

        self.groups[decl.name] = decl

    # ------------------------------------------------------------------
    # Step 2a:
    # Reference checks
    # ------------------------------------------------------------------

    def _check_references(self, exam: ExamDeclaration):
        """
        Verify that every exam refers to declared resources.

        Checks:

            - room exists
            - invigilator exists
            - student group exists

        These checks are performed even when slot == 0.
        """

        # --------------------------------------------------------------
        # Room reference
        # --------------------------------------------------------------

        if exam.room not in self.rooms:
            raise SemanticAnalysisError(
                f"Room '{exam.room}' is not declared.",
                category="Undeclared Reference",
                line=exam.line,
                column=exam.column,
            )

        # --------------------------------------------------------------
        # Invigilator reference
        # --------------------------------------------------------------

        if exam.invigilator not in self.invigilators:
            raise SemanticAnalysisError(
                f"Invigilator '{exam.invigilator}' is not declared.",
                category="Undeclared Reference",
                line=exam.line,
                column=exam.column,
            )

        # --------------------------------------------------------------
        # Student group reference
        # --------------------------------------------------------------

        if exam.students not in self.groups:
            raise SemanticAnalysisError(
                f"Student group '{exam.students}' is not declared.",
                category="Undeclared Reference",
                line=exam.line,
                column=exam.column,
            )

    # ------------------------------------------------------------------
    # Step 2b:
    # Room capacity check
    # ------------------------------------------------------------------

    def _check_room_capacity(self, exam: ExamDeclaration):
        """
        Verify that the assigned room can accommodate the
        assigned student group.

        This check is performed even when slot == 0 because
        room capacity does not depend on the timetable slot.
        """

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
    # Step 2c:
    # Room conflict check
    # ------------------------------------------------------------------

    def _check_room_conflict(self, exam: ExamDeclaration):
        """
        Verify that a room is not used by two exams
        in the same slot.
        """

        key = (exam.room, exam.slot)

        if key in self._room_bookings:
            raise SemanticAnalysisError(
                f"Room '{exam.room}' is already booked "
                f"in slot {exam.slot}.",
                category="Room Conflict",
                line=exam.line,
                column=exam.column,
            )

        self._room_bookings[key] = exam.course

    # ------------------------------------------------------------------
    # Invigilator conflict check
    # ------------------------------------------------------------------

    def _check_invigilator_conflict(self, exam: ExamDeclaration):
        """
        Verify that an invigilator is not assigned to two exams
        in the same slot.
        """

        key = (exam.invigilator, exam.slot)

        if key in self._invigilator_bookings:
            raise SemanticAnalysisError(
                f"Invigilator '{exam.invigilator}' is already "
                f"assigned in slot {exam.slot}.",
                category="Invigilator Conflict",
                line=exam.line,
                column=exam.column,
            )

        self._invigilator_bookings[key] = exam.course

    # ------------------------------------------------------------------
    # Student group conflict check
    # ------------------------------------------------------------------

    def _check_group_conflict(self, exam: ExamDeclaration):
        """
        Verify that a student group does not have two exams
        in the same slot.
        """

        key = (exam.students, exam.slot)

        if key in self._group_bookings:
            raise SemanticAnalysisError(
                f"Student group '{exam.students}' already has "
                f"an exam in slot {exam.slot}.",
                category="Group Conflict",
                line=exam.line,
                column=exam.column,
            )

        self._group_bookings[key] = exam.course


# ----------------------------------------------------------------------
# Display helper
# ----------------------------------------------------------------------

def format_symbol_tables(analyzer: SemanticAnalyzer) -> str:
    """
    Render the analyzer's symbol tables as readable text.

    This is used by main.py for displaying the semantic-analysis
    results during compiler execution.
    """

    lines = []

    # --------------------------------------------------------------
    # Rooms
    # --------------------------------------------------------------

    lines.append("Rooms:")

    if analyzer.rooms:
        for name, room in analyzer.rooms.items():
            lines.append(
                f"  {name} -> capacity {room.capacity}"
            )
    else:
        lines.append("  (none declared)")

    # --------------------------------------------------------------
    # Invigilators
    # --------------------------------------------------------------

    lines.append("Invigilators:")

    if analyzer.invigilators:
        for name in analyzer.invigilators:
            lines.append(f"  {name}")
    else:
        lines.append("  (none declared)")

    # --------------------------------------------------------------
    # Student Groups
    # --------------------------------------------------------------

    lines.append("Student Groups:")

    if analyzer.groups:
        for name, group in analyzer.groups.items():
            lines.append(
                f"  {name} -> size {group.size}"
            )
    else:
        lines.append("  (none declared)")

    # --------------------------------------------------------------
    # Exams
    # --------------------------------------------------------------

    lines.append("Exams:")

    if analyzer.exams:
        for exam in analyzer.exams:
            slot_display = f"{exam.slot} (AUTO)" if exam.slot == AUTO_SLOT else f"{exam.slot}"
            lines.append(
                f"  {exam.course}: "
                f"room={exam.room}, "
                f"invigilator={exam.invigilator}, "
                f"students={exam.students}, "
                f"slot={slot_display}"
            )
    else:
        lines.append("  (none declared)")

    return "\n".join(lines)
