"""
tokens.py
=========

Defines the token categories and the Token data structure used by the
TimetableLang lexer and parser.

A Token is the smallest meaningful unit produced by lexical analysis.
Each token carries:
    - type   : what kind of token it is (see TokenType)
    - value  : the actual text/lexeme (or its Python value for NUMBER)
    - line   : the source line number where the token starts (1-based)
    - column : the source column number where the token starts (1-based)
"""

from enum import Enum, auto


class TokenType(Enum):
    """All token categories recognized by the TimetableLang lexer."""

    KEYWORD = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    SEMICOLON = auto()
    EOF = auto()


# The fixed set of reserved words in TimetableLang.
# Any identifier-looking word that matches one of these is tokenized
# as a KEYWORD instead of an IDENTIFIER.
KEYWORDS = {
    "room",
    "capacity",
    "invigilator",
    "group",
    "size",
    "exam",
    "students",
    "slot",
}


class Token:
    """A single lexical token with source position information."""

    def __init__(self, type_: TokenType, value, line: int, column: int):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return (
            f"Token(type={self.type.name}, value={self.value!r}, "
            f"line={self.line}, column={self.column})"
        )

    def __eq__(self, other):
        if not isinstance(other, Token):
            return NotImplemented
        return (
            self.type == other.type
            and self.value == other.value
            and self.line == other.line
            and self.column == other.column
        )
