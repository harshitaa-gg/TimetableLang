"""
test_timetable_generator.py
===========================

Unit and integration tests for the TimetableLang generator and independent
verifier (src/timetable_generator.py) — Phase 3.

Includes tests for:
    - Fixed slot (pinned) assignments
    - AUTO slot (slot 0) assignments
    - Mixed fixed and AUTO assignments
    - Backtracking slot search
    - Max slots boundary conditions and failures
    - Safety-net checks (capacity, declarations)
    - Independent verification (verify_timetable)
    - Integration tests against examples/*.tt files

Run with:
    python -m unittest tests.test_timetable_generator
"""

import os
import unittest

from src.lexer import Lexer
from src.parser import Parser
from src.semantic_analyzer import SemanticAnalyzer
from src.timetable_generator import (
    TimetableGenerator,
    TimetableGenerationError,
    Timetable,
    Assignment,
    verify_timetable,
    format_timetable,
    format_timetable_by_slot,
)

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def compile_and_generate(source: str, max_slots=None):
    """Helper: run full pipeline up to timetable generator."""
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse_program()
    analyzer = SemanticAnalyzer(program)
    analyzer.analyze()
    generator = TimetableGenerator(analyzer, max_slots=max_slots)
    timetable = generator.generate()
    return analyzer, timetable


def generate_from_file(filename: str, max_slots=None):
    """Helper: run full pipeline on a file under examples/."""
    path = os.path.join(EXAMPLES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return compile_and_generate(source, max_slots=max_slots)


class TestTimetableGenerator(unittest.TestCase):

    def test_fixed_slots_honored(self):
        source = """
        room hall_a capacity 100;
        room hall_b capacity 100;
        invigilator prof_x;
        invigilator prof_y;
        group cse_a size 50;
        group cse_b size 50;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        exam CS102 room hall_b invigilator prof_y students cse_b slot 2;
        """
        analyzer, timetable = compile_and_generate(source)
        self.assertEqual(len(timetable.assignments), 2)
        slots = {a.course: a.slot for a in timetable.assignments}
        self.assertEqual(slots["CS101"], 1)
        self.assertEqual(slots["CS102"], 2)

        # Independent verifier check
        violations = verify_timetable(timetable, analyzer=analyzer)
        self.assertEqual(violations, [])

    def test_auto_slots_assigned_without_conflict(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 50;
        group cse_b size 50;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 0;
        exam CS102 room hall_a invigilator prof_x students cse_b slot 0;
        """
        analyzer, timetable = compile_and_generate(source)
        self.assertEqual(len(timetable.assignments), 2)
        # Because both exams share hall_a and prof_x, they cannot be in the same slot
        slots = {a.course: a.slot for a in timetable.assignments}
        self.assertNotEqual(slots["CS101"], slots["CS102"])
        self.assertTrue(all(s >= 1 for s in slots.values()))

        # Independent verifier check
        violations = verify_timetable(timetable, analyzer=analyzer)
        self.assertEqual(violations, [])

    def test_mixed_fixed_and_auto_slots(self):
        source = """
        room hall_a capacity 100;
        room hall_b capacity 100;
        invigilator prof_x;
        invigilator prof_y;
        group cse_a size 50;
        group cse_b size 50;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        exam CS102 room hall_a invigilator prof_y students cse_b slot 0;
        """
        analyzer, timetable = compile_and_generate(source)
        slots = {a.course: a.slot for a in timetable.assignments}
        # Fixed CS101 must stay in slot 1
        self.assertEqual(slots["CS101"], 1)
        # AUTO CS102 shares hall_a so must NOT be in slot 1
        self.assertNotEqual(slots["CS102"], 1)

        # Independent verifier check
        violations = verify_timetable(timetable, analyzer=analyzer)
        self.assertEqual(violations, [])

    def test_backtracking_finds_valid_schedule(self):
        source = """
        room hall_a capacity 100;
        room hall_b capacity 100;
        invigilator prof_x;
        invigilator prof_y;
        group cse_a size 50;
        group cse_b size 50;
        group cse_c size 50;

        exam CS101 room hall_a invigilator prof_x students cse_a slot 0;
        exam CS102 room hall_b invigilator prof_x students cse_b slot 0;
        exam CS103 room hall_a invigilator prof_y students cse_c slot 0;
        """
        analyzer, timetable = compile_and_generate(source, max_slots=2)
        self.assertEqual(len(timetable.assignments), 3)

        violations = verify_timetable(timetable, analyzer=analyzer, max_slots=2)
        self.assertEqual(violations, [])

    def test_insufficient_slots_raises_error(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 50;
        group cse_b size 50;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 0;
        exam CS102 room hall_a invigilator prof_x students cse_b slot 0;
        """
        # 2 exams sharing room & invigilator cannot fit in 1 slot
        with self.assertRaises(TimetableGenerationError) as ctx:
            compile_and_generate(source, max_slots=1)
        self.assertIn("Could not assign", str(ctx.exception))

    def test_empty_program_yields_empty_timetable(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 50;
        """
        analyzer, timetable = compile_and_generate(source)
        self.assertEqual(len(timetable.assignments), 0)
        self.assertEqual(timetable.slot_count, 0)
        violations = verify_timetable(timetable, analyzer=analyzer)
        self.assertEqual(violations, [])

    def test_format_helpers(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 50;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        """
        _, timetable = compile_and_generate(source)
        formatted = format_timetable(timetable)
        self.assertIn("CS101", formatted)
        self.assertIn("hall_a", formatted)
        self.assertIn("prof_x", formatted)
        self.assertIn("cse_a", formatted)

        slot_view = format_timetable_by_slot(timetable)
        self.assertIn("Slot 1:", slot_view)
        self.assertIn("CS101", slot_view)


class TestIndependentVerifier(unittest.TestCase):

    def test_verifier_catches_room_conflict(self):
        t = Timetable(
            assignments=[
                Assignment("CS101", "hall_a", "prof_x", "cse_a", 1),
                Assignment("CS102", "hall_a", "prof_y", "cse_b", 1),
            ],
            slot_count=2,
        )
        problems = verify_timetable(t)
        self.assertTrue(any("Room 'hall_a' is double-booked" in p for p in problems))

    def test_verifier_catches_invigilator_conflict(self):
        t = Timetable(
            assignments=[
                Assignment("CS101", "hall_a", "prof_x", "cse_a", 1),
                Assignment("CS102", "hall_b", "prof_x", "cse_b", 1),
            ],
            slot_count=2,
        )
        problems = verify_timetable(t)
        self.assertTrue(any("Invigilator 'prof_x' is double-booked" in p for p in problems))

    def test_verifier_catches_group_conflict(self):
        t = Timetable(
            assignments=[
                Assignment("CS101", "hall_a", "prof_x", "cse_a", 1),
                Assignment("CS102", "hall_b", "prof_y", "cse_a", 1),
            ],
            slot_count=2,
        )
        problems = verify_timetable(t)
        self.assertTrue(any("Student group 'cse_a' is double-booked" in p for p in problems))

    def test_verifier_catches_invalid_slot_number(self):
        t = Timetable(
            assignments=[
                Assignment("CS101", "hall_a", "prof_x", "cse_a", 0),
            ],
            slot_count=2,
        )
        problems = verify_timetable(t)
        self.assertTrue(any("invalid non-positive slot 0" in p for p in problems))


class TestIntegrationExampleFiles(unittest.TestCase):

    def test_valid_small_generates_and_verifies(self):
        analyzer, timetable = generate_from_file("valid_small.tt")
        self.assertEqual(len(timetable.assignments), 1)
        violations = verify_timetable(timetable, analyzer=analyzer)
        self.assertEqual(violations, [])

    def test_valid_large_generates_and_verifies(self):
        analyzer, timetable = generate_from_file("valid_large.tt")
        self.assertEqual(len(timetable.assignments), 7)
        violations = verify_timetable(timetable, analyzer=analyzer)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
