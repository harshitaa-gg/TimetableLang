"""
test_parser.py
===============

Unit tests for the TimetableLang recursive-descent parser
(src/parser.py).

Run with:
    python -m unittest discover -s tests
or simply:
    python -m unittest tests.test_parser
"""

import unittest

from src.lexer import Lexer
from src.parser import Parser, SyntaxAnalysisError
from src.ast_nodes import (
    RoomDeclaration,
    InvigilatorDeclaration,
    GroupDeclaration,
    ExamDeclaration,
)


def parse(source: str):
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse_program()


class TestParserValidPrograms(unittest.TestCase):

    def test_empty_program(self):
        program = parse("")
        self.assertEqual(program.declarations, [])

    def test_single_room_declaration(self):
        program = parse("room hall_a capacity 100;")
        self.assertEqual(len(program.declarations), 1)
        decl = program.declarations[0]
        self.assertIsInstance(decl, RoomDeclaration)
        self.assertEqual(decl.name, "hall_a")
        self.assertEqual(decl.capacity, 100)

    def test_single_invigilator_declaration(self):
        program = parse("invigilator prof_x;")
        decl = program.declarations[0]
        self.assertIsInstance(decl, InvigilatorDeclaration)
        self.assertEqual(decl.name, "prof_x")

    def test_single_group_declaration(self):
        program = parse("group cse_a size 80;")
        decl = program.declarations[0]
        self.assertIsInstance(decl, GroupDeclaration)
        self.assertEqual(decl.name, "cse_a")
        self.assertEqual(decl.size, 80)

    def test_single_exam_declaration(self):
        source = (
            "exam CS101\n"
            " room hall_a\n"
            " invigilator prof_x\n"
            " students cse_a\n"
            " slot 1;"
        )
        program = parse(source)
        decl = program.declarations[0]
        self.assertIsInstance(decl, ExamDeclaration)
        self.assertEqual(decl.course, "CS101")
        self.assertEqual(decl.room, "hall_a")
        self.assertEqual(decl.invigilator, "prof_x")
        self.assertEqual(decl.students, "cse_a")
        self.assertEqual(decl.slot, 1)

    def test_multiple_declarations_of_all_kinds(self):
        source = """
        room hall_a capacity 100;
        room hall_b capacity 80;
        invigilator prof_x;
        invigilator prof_y;
        group cse_a size 75;
        group ece_a size 60;
        exam CS101
         room hall_a
         invigilator prof_x
         students cse_a
         slot 1;
        exam EC101
         room hall_b
         invigilator prof_y
         students ece_a
         slot 1;
        """
        program = parse(source)
        self.assertEqual(len(program.declarations), 8)
        kinds = [type(d).__name__ for d in program.declarations]
        self.assertEqual(
            kinds,
            [
                "RoomDeclaration",
                "RoomDeclaration",
                "InvigilatorDeclaration",
                "InvigilatorDeclaration",
                "GroupDeclaration",
                "GroupDeclaration",
                "ExamDeclaration",
                "ExamDeclaration",
            ],
        )

    def test_different_whitespace_formatting_is_accepted(self):
        source = "room   hall_a\ncapacity\t100 ;"
        program = parse(source)
        decl = program.declarations[0]
        self.assertIsInstance(decl, RoomDeclaration)
        self.assertEqual(decl.name, "hall_a")
        self.assertEqual(decl.capacity, 100)


class TestParserSyntaxErrors(unittest.TestCase):

    def test_missing_keyword(self):
        with self.assertRaises(SyntaxAnalysisError):
            parse("room hall_a 100;")

    def test_missing_identifier(self):
        with self.assertRaises(SyntaxAnalysisError):
            parse("room capacity 100;")

    def test_missing_number(self):
        with self.assertRaises(SyntaxAnalysisError):
            parse("room hall_a capacity;")

    def test_missing_semicolon(self):
        with self.assertRaises(SyntaxAnalysisError):
            parse("room hall_a capacity 100")

    def test_wrong_declaration_order(self):
        with self.assertRaises(SyntaxAnalysisError):
            parse("room capacity hall_a 100;")

    def test_missing_exam_field(self):
        source = (
            "exam CS101\n"
            " room hall_a\n"
            " invigilator prof_x\n"
            " slot 1;"
        )
        with self.assertRaises(SyntaxAnalysisError):
            parse(source)

    def test_unexpected_token(self):
        source = (
            "exam CS101\n"
            " room hall_a\n"
            " professor prof_x\n"
            " students cse_a\n"
            " slot 1;"
        )
        with self.assertRaises(SyntaxAnalysisError):
            parse(source)

    def test_error_message_includes_line_and_column(self):
        try:
            parse("room hall_a 100;")
        except SyntaxAnalysisError as e:
            self.assertIsInstance(e.line, int)
            self.assertIsInstance(e.column, int)
        else:
            self.fail("Expected SyntaxAnalysisError was not raised")


if __name__ == "__main__":
    unittest.main()
