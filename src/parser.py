"""
parser.py
=========

The Parser (syntax analyzer) for TimetableLang.

Responsibility: consume the token stream produced by the Lexer and
check whether it conforms to the TimetableLang grammar (see the
project document, section 12). If it does, build an AST (see
ast_nodes.py) representing the logical structure of the program.

This is implemented as a RECURSIVE-DESCENT PARSER: each grammar rule
is implemented as one Python method, and methods call each other in
the same shape as the grammar itself.

Grammar implemented here:

    Program            -> DeclarationList
    DeclarationList    -> Declaration DeclarationList | epsilon
    Declaration        -> RoomDeclaration
                         | InvigilatorDeclaration
                         | GroupDeclaration
                         | ExamDeclaration
    RoomDeclaration    -> "room" IDENTIFIER "capacity" NUMBER ";"
    InvigilatorDeclaration -> "invigilator" IDENTIFIER ";"
    GroupDeclaration   -> "group" IDENTIFIER "size" NUMBER ";"
    ExamDeclaration    -> "exam" IDENTIFIER
                          "room" IDENTIFIER
                          "invigilator" IDENTIFIER
                          "students" IDENTIFIER
                          "slot" NUMBER ";"

The parser does NOT check whether a referenced room/invigilator/group
actually exists, whether capacities are sufficient, or whether there
are scheduling conflicts. Those are Phase 2 (semantic analysis)
concerns and are intentionally out of scope here.
"""

from .tokens import TokenType
from .ast_nodes import (
    Program,
    RoomDeclaration,
    InvigilatorDeclaration,
    GroupDeclaration,
    ExamDeclaration,
)


class SyntaxAnalysisError(Exception):
    """Raised when the token stream does not conform to the grammar."""

    def __init__(self, message: str, line: int, column: int):
        self.line = line
        self.column = column
        super().__init__(
            f"Syntax Error (line {line}, column {column}): {message}"
        )


class Parser:
    """Recursive-descent parser: Token stream -> AST (Program node)."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0  # index of the current token in self.tokens

    # ------------------------------------------------------------------
    # Low-level token helpers
    # ------------------------------------------------------------------

    def _current(self):
        """Return the token currently being looked at (never past EOF)."""
        return self.tokens[self.pos]

    def _advance(self):
        """Consume and return the current token, moving to the next one."""
        token = self.tokens[self.pos]
        if token.type != TokenType.EOF:
            self.pos += 1
        return token

    def _check_keyword(self, keyword_text):
        """True if the current token is the KEYWORD with this exact text."""
        token = self._current()
        return token.type == TokenType.KEYWORD and token.value == keyword_text

    def _expect_keyword(self, keyword_text):
        """
        Consume the current token if it is the expected keyword.
        Otherwise raise a SyntaxAnalysisError describing what was
        expected vs what was actually found.
        """
        token = self._current()
        if self._check_keyword(keyword_text):
            return self._advance()
        raise SyntaxAnalysisError(
            f"Expected keyword '{keyword_text}' but found "
            f"{self._describe(token)}",
            token.line,
            token.column,
        )

    def _expect_type(self, token_type, description):
        """
        Consume the current token if it matches the expected TokenType.
        Otherwise raise a SyntaxAnalysisError.
        """
        token = self._current()
        if token.type == token_type:
            return self._advance()
        raise SyntaxAnalysisError(
            f"Expected {description} but found {self._describe(token)}",
            token.line,
            token.column,
        )

    @staticmethod
    def _describe(token):
        """Human-readable description of a token, used in error messages."""
        if token.type == TokenType.EOF:
            return "end of file"
        return f"{token.type.name} '{token.value}'"

    # ------------------------------------------------------------------
    # Grammar rules
    # ------------------------------------------------------------------

    def parse_program(self):
        """
        Program -> DeclarationList

        Top-level entry point. Parses declarations until EOF is
        reached and wraps them in a Program AST node.
        """
        declarations = []
        while self._current().type != TokenType.EOF:
            declarations.append(self._parse_declaration())
        return Program(declarations)

    def _parse_declaration(self):
        """
        Declaration -> RoomDeclaration
                     | InvigilatorDeclaration
                     | GroupDeclaration
                     | ExamDeclaration

        Dispatches to the correct rule based on the current keyword.
        """
        token = self._current()

        if token.type == TokenType.KEYWORD and token.value == "room":
            return self._parse_room_declaration()
        if token.type == TokenType.KEYWORD and token.value == "invigilator":
            return self._parse_invigilator_declaration()
        if token.type == TokenType.KEYWORD and token.value == "group":
            return self._parse_group_declaration()
        if token.type == TokenType.KEYWORD and token.value == "exam":
            return self._parse_exam_declaration()

        raise SyntaxAnalysisError(
            "Expected the start of a declaration "
            "('room', 'invigilator', 'group', or 'exam') "
            f"but found {self._describe(token)}",
            token.line,
            token.column,
        )

    def _parse_room_declaration(self):
        """RoomDeclaration -> "room" IDENTIFIER "capacity" NUMBER ";" """
        start = self._expect_keyword("room")
        name_token = self._expect_type(TokenType.IDENTIFIER, "an identifier (room name)")
        self._expect_keyword("capacity")
        capacity_token = self._expect_type(TokenType.NUMBER, "a number (room capacity)")
        self._expect_type(TokenType.SEMICOLON, "';' to end the room declaration")

        return RoomDeclaration(
            name=name_token.value,
            capacity=capacity_token.value,
            line=start.line,
            column=start.column,
        )

    def _parse_invigilator_declaration(self):
        """InvigilatorDeclaration -> "invigilator" IDENTIFIER ";" """
        start = self._expect_keyword("invigilator")
        name_token = self._expect_type(
            TokenType.IDENTIFIER, "an identifier (invigilator name)"
        )
        self._expect_type(TokenType.SEMICOLON, "';' to end the invigilator declaration")

        return InvigilatorDeclaration(
            name=name_token.value, line=start.line, column=start.column
        )

    def _parse_group_declaration(self):
        """GroupDeclaration -> "group" IDENTIFIER "size" NUMBER ";" """
        start = self._expect_keyword("group")
        name_token = self._expect_type(TokenType.IDENTIFIER, "an identifier (group name)")
        self._expect_keyword("size")
        size_token = self._expect_type(TokenType.NUMBER, "a number (group size)")
        self._expect_type(TokenType.SEMICOLON, "';' to end the group declaration")

        return GroupDeclaration(
            name=name_token.value,
            size=size_token.value,
            line=start.line,
            column=start.column,
        )

    def _parse_exam_declaration(self):
        """
        ExamDeclaration -> "exam" IDENTIFIER
                           "room" IDENTIFIER
                           "invigilator" IDENTIFIER
                           "students" IDENTIFIER
                           "slot" NUMBER ";"
        """
        start = self._expect_keyword("exam")
        course_token = self._expect_type(TokenType.IDENTIFIER, "an identifier (course name)")

        self._expect_keyword("room")
        room_token = self._expect_type(TokenType.IDENTIFIER, "an identifier (room name)")

        self._expect_keyword("invigilator")
        invigilator_token = self._expect_type(
            TokenType.IDENTIFIER, "an identifier (invigilator name)"
        )

        self._expect_keyword("students")
        students_token = self._expect_type(
            TokenType.IDENTIFIER, "an identifier (student group name)"
        )

        self._expect_keyword("slot")
        slot_token = self._expect_type(TokenType.NUMBER, "a number (slot number)")

        self._expect_type(TokenType.SEMICOLON, "';' to end the exam declaration")

        return ExamDeclaration(
            course=course_token.value,
            room=room_token.value,
            invigilator=invigilator_token.value,
            students=students_token.value,
            slot=slot_token.value,
            line=start.line,
            column=start.column,
        )
