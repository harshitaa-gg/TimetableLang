"""
lexer.py
========

The Lexer (lexical analyzer) for TimetableLang.

Responsibility: convert raw TimetableLang source text into a flat
stream of Token objects (see tokens.py). This is the FIRST phase of
the compiler pipeline:

    Source Code -> [LEXER] -> Token Stream -> Parser -> AST

The lexer answers only ONE question: "Can this text be broken into
valid TimetableLang tokens?". It does NOT know anything about grammar
rules (that is the parser's job) or about whether rooms/invigilators
actually exist (that is Phase 2 semantic analysis).

Supported token categories (see TokenType):
    KEYWORD, IDENTIFIER, NUMBER, SEMICOLON, EOF

Whitespace (spaces, tabs, newlines) is ignored/skipped, but newlines
are used to keep line/column tracking accurate.

Any character that cannot start a valid token (for example '@', '#',
'$') results in a LexicalError with the offending character and its
exact source position.
"""

from .tokens import Token, TokenType, KEYWORDS


class LexicalError(Exception):
    """Raised when the lexer encounters an invalid character."""

    def __init__(self, message: str, line: int, column: int):
        self.line = line
        self.column = column
        super().__init__(
            f"Lexical Error (line {line}, column {column}): {message}"
        )


class Lexer:
    """Turns TimetableLang source text into a list of Token objects."""

    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0        # index into self.source
        self.line = 1       # current line number (1-based)
        self.column = 1     # current column number (1-based)

    # ------------------------------------------------------------------
    # Low-level character helpers
    # ------------------------------------------------------------------

    def _current_char(self):
        """Return the character at self.pos, or None if past the end."""
        if self.pos >= self.length:
            return None
        return self.source[self.pos]

    def _advance(self):
        """Move forward by one character, updating line/column tracking."""
        char = self._current_char()
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1
        return char

    def _skip_whitespace(self):
        """Skip spaces, tabs, carriage returns, and newlines."""
        while self._current_char() is not None and self._current_char() in " \t\r\n":
            self._advance()

    # ------------------------------------------------------------------
    # Token producers
    # ------------------------------------------------------------------

    def _read_identifier_or_keyword(self):
        """
        Reads a run of letters/digits/underscores starting from the
        current position and classifies it as KEYWORD or IDENTIFIER.

        Identifier rule used by TimetableLang:
            - must start with a letter or underscore
            - may continue with letters, digits, or underscores
        This covers names like hall_a, prof_x, cse_a, CS101, CS201.
        """
        start_line = self.line
        start_column = self.column
        chars = []

        while self._current_char() is not None and (
            self._current_char().isalnum() or self._current_char() == "_"
        ):
            chars.append(self._advance())

        text = "".join(chars)

        if text in KEYWORDS:
            return Token(TokenType.KEYWORD, text, start_line, start_column)
        return Token(TokenType.IDENTIFIER, text, start_line, start_column)

    def _read_number(self):
        """
        Reads a run of digits starting from the current position and
        produces a NUMBER token. TimetableLang numbers are simple
        non-negative integers (capacities, sizes, slot numbers).
        """
        start_line = self.line
        start_column = self.column
        digits = []

        while self._current_char() is not None and self._current_char().isdigit():
            digits.append(self._advance())

        value = int("".join(digits))
        return Token(TokenType.NUMBER, value, start_line, start_column)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self):
        """
        Scans the entire source and returns a list of Token objects,
        ending with a single EOF token.

        Raises:
            LexicalError: if an invalid character is encountered.
        """
        tokens = []

        while True:
            self._skip_whitespace()
            char = self._current_char()

            if char is None:
                tokens.append(Token(TokenType.EOF, None, self.line, self.column))
                break

            if char == ";":
                line, column = self.line, self.column
                self._advance()
                tokens.append(Token(TokenType.SEMICOLON, ";", line, column))
                continue

            if char.isalpha() or char == "_":
                tokens.append(self._read_identifier_or_keyword())
                continue

            if char.isdigit():
                tokens.append(self._read_number())
                continue

            # Anything else is not a valid TimetableLang character.
            raise LexicalError(
                f"Invalid character '{char}'", self.line, self.column
            )

        return tokens
