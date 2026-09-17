"""
test_lexer.py
=============

Unit tests for the TimetableLang lexer (src/lexer.py).

Run with:
    python -m unittest discover -s tests
or simply:
    python -m unittest tests.test_lexer
"""

import unittest

from src.lexer import Lexer, LexicalError
from src.tokens import TokenType


class TestLexer(unittest.TestCase):

    def test_room_declaration_tokens(self):
        tokens = Lexer("room hall_a capacity 100;").tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(
            types,
            [
                TokenType.KEYWORD,
                TokenType.IDENTIFIER,
                TokenType.KEYWORD,
                TokenType.NUMBER,
                TokenType.SEMICOLON,
                TokenType.EOF,
            ],
        )
        self.assertEqual(tokens[0].value, "room")
        self.assertEqual(tokens[1].value, "hall_a")
        self.assertEqual(tokens[2].value, "capacity")
        self.assertEqual(tokens[3].value, 100)

    def test_invigilator_declaration_tokens(self):
        tokens = Lexer("invigilator prof_x;").tokenize()
        self.assertEqual(tokens[0].value, "invigilator")
        self.assertEqual(tokens[1].value, "prof_x")
        self.assertEqual(tokens[2].type, TokenType.SEMICOLON)

    def test_group_declaration_tokens(self):
        tokens = Lexer("group cse_a size 80;").tokenize()
        values = [t.value for t in tokens[:-1]]  # drop EOF
        self.assertEqual(values, ["group", "cse_a", "size", 80, ";"])

    def test_identifier_with_digits_like_course_code(self):
        tokens = Lexer("exam CS101 room hall_a invigilator prof_x students cse_a slot 1;").tokenize()
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].value, "CS101")

    def test_whitespace_and_newlines_are_ignored(self):
        source = "room\n   hall_a\tcapacity\n100 ;"
        tokens = Lexer(source).tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(
            types,
            [
                TokenType.KEYWORD,
                TokenType.IDENTIFIER,
                TokenType.KEYWORD,
                TokenType.NUMBER,
                TokenType.SEMICOLON,
                TokenType.EOF,
            ],
        )

    def test_empty_source_produces_only_eof(self):
        tokens = Lexer("").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

    def test_invalid_character_raises_lexical_error(self):
        with self.assertRaises(LexicalError) as ctx:
            Lexer("room hall_a capacity @100;").tokenize()
        self.assertIn("@", str(ctx.exception))

    def test_line_and_column_tracking(self):
        source = "room hall_a capacity 100;\ninvigilator prof_x;"
        tokens = Lexer(source).tokenize()
        # 'invigilator' should be on line 2, column 1
        invigilator_token = next(t for t in tokens if t.value == "invigilator")
        self.assertEqual(invigilator_token.line, 2)
        self.assertEqual(invigilator_token.column, 1)


if __name__ == "__main__":
    unittest.main()
