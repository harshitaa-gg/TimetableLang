"""
test_semantic_analyzer.py
==========================

Unit tests for the TimetableLang semantic analyzer
(src/semantic_analyzer.py) — Phase 2.

Includes:
    - Direct unit tests against small inline source snippets covering
      each of the 10 required semantic checks.
    - Integration-style tests that run the full pipeline (lexer ->
      parser -> semantic analyzer) against every example file in
      examples/, to confirm valid files still pass and every
      semantic_*.tt file fails with the expected error category.

Run with:
    python -m unittest discover -s tests -v
or simply:
    python -m unittest tests.test_semantic_analyzer
"""

import os
import unittest

from src.lexer import Lexer
from src.parser import Parser
from src.semantic_analyzer import SemanticAnalyzer, SemanticAnalysisError

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def analyze_source(source: str):
    """Helper: run lexer -> parser -> semantic analyzer on a source
    string and return the analyzer (already analyzed)."""
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse_program()
    analyzer = SemanticAnalyzer(program)
    analyzer.analyze()
    return analyzer


def analyze_file(filename: str):
    """Helper: run the full pipeline against a file under examples/."""
    path = os.path.join(EXAMPLES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return analyze_source(source)


class TestSemanticAnalyzerValidPrograms(unittest.TestCase):

    def test_valid_program_passes(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 80;
        exam CS101
         room hall_a
         invigilator prof_x
         students cse_a
         slot 1;
        """
        analyzer = analyze_source(source)
        self.assertIn("hall_a", analyzer.rooms)
        self.assertIn("prof_x", analyzer.invigilators)
        self.assertIn("cse_a", analyzer.groups)
        self.assertEqual(len(analyzer.exams), 1)

    def test_same_room_different_slots_is_allowed(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 40;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        exam CS102 room hall_a invigilator prof_x students cse_a slot 2;
        """
        # Same room, invigilator, and group reused, but different
        # slots -> no conflict.
        analyze_source(source)  # should not raise

    def test_valid_small_example_file_passes(self):
        analyze_file("valid_small.tt")  # should not raise

    def test_valid_large_example_file_passes(self):
        analyze_file("valid_large.tt")  # should not raise


class TestSemanticAnalyzerDuplicateDeclarations(unittest.TestCase):

    def test_duplicate_room(self):
        source = """
        room hall_a capacity 100;
        room hall_a capacity 200;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Duplicate Declaration")
        self.assertIn("hall_a", str(ctx.exception))

    def test_duplicate_invigilator(self):
        source = """
        invigilator prof_x;
        invigilator prof_x;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Duplicate Declaration")
        self.assertIn("prof_x", str(ctx.exception))

    def test_duplicate_group(self):
        source = """
        group cse_a size 80;
        group cse_a size 90;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Duplicate Declaration")
        self.assertIn("cse_a", str(ctx.exception))

    def test_example_files_for_duplicates(self):
        for filename in (
            "semantic_duplicate_room.tt",
            "semantic_duplicate_invigilator.tt",
            "semantic_duplicate_group.tt",
        ):
            with self.assertRaises(SemanticAnalysisError, msg=filename):
                analyze_file(filename)


class TestSemanticAnalyzerUndeclaredReferences(unittest.TestCase):

    def test_unknown_room_reference(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 80;
        exam CS101
         room hall_b
         invigilator prof_x
         students cse_a
         slot 1;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Undeclared Reference")
        self.assertIn("hall_b", str(ctx.exception))

    def test_unknown_invigilator_reference(self):
        source = """
        room hall_a capacity 100;
        group cse_a size 80;
        exam CS101
         room hall_a
         invigilator prof_x
         students cse_a
         slot 1;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Undeclared Reference")
        self.assertIn("prof_x", str(ctx.exception))

    def test_unknown_group_reference(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        exam CS101
         room hall_a
         invigilator prof_x
         students cse_a
         slot 1;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Undeclared Reference")
        self.assertIn("cse_a", str(ctx.exception))

    def test_example_files_for_undeclared_references(self):
        for filename in (
            "semantic_unknown_room.tt",
            "semantic_unknown_invigilator.tt",
            "semantic_unknown_group.tt",
        ):
            with self.assertRaises(SemanticAnalysisError, msg=filename):
                analyze_file(filename)


class TestSemanticAnalyzerCapacity(unittest.TestCase):

    def test_capacity_violation(self):
        source = """
        room hall_a capacity 50;
        invigilator prof_x;
        group cse_a size 80;
        exam CS101
         room hall_a
         invigilator prof_x
         students cse_a
         slot 1;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Capacity Violation")
        message = str(ctx.exception)
        self.assertIn("50", message)
        self.assertIn("80", message)

    def test_capacity_exactly_equal_is_allowed(self):
        source = """
        room hall_a capacity 80;
        invigilator prof_x;
        group cse_a size 80;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        """
        analyze_source(source)  # should not raise; equal capacity is fine

    def test_example_file_for_capacity_violation(self):
        with self.assertRaises(SemanticAnalysisError):
            analyze_file("semantic_capacity_violation.tt")


class TestSemanticAnalyzerConflicts(unittest.TestCase):

    def test_room_double_booking(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        invigilator prof_y;
        group cse_a size 40;
        group cse_b size 40;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        exam CS102 room hall_a invigilator prof_y students cse_b slot 1;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Room Conflict")

    def test_invigilator_double_booking(self):
        source = """
        room hall_a capacity 100;
        room hall_b capacity 100;
        invigilator prof_x;
        group cse_a size 40;
        group cse_b size 40;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        exam CS102 room hall_b invigilator prof_x students cse_b slot 1;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Invigilator Conflict")

    def test_group_clash(self):
        source = """
        room hall_a capacity 100;
        room hall_b capacity 100;
        invigilator prof_x;
        invigilator prof_y;
        group cse_a size 40;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        exam CS102 room hall_b invigilator prof_y students cse_a slot 1;
        """
        with self.assertRaises(SemanticAnalysisError) as ctx:
            analyze_source(source)
        self.assertEqual(ctx.exception.category, "Group Conflict")

    def test_example_files_for_conflicts(self):
        cases = {
            "semantic_room_conflict.tt": "Room Conflict",
            "semantic_invigilator_conflict.tt": "Invigilator Conflict",
            "semantic_group_conflict.tt": "Group Conflict",
        }
        for filename, expected_category in cases.items():
            with self.assertRaises(SemanticAnalysisError) as ctx:
                analyze_file(filename)
            self.assertEqual(ctx.exception.category, expected_category, filename)


if __name__ == "__main__":
    unittest.main()
