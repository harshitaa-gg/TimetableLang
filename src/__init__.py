"""
TimetableLang Compiler Package
==============================

Components:
  - tokens.py              : Token and TokenType definitions (Phase 1)
  - lexer.py               : Lexical analyzer (source code -> tokens) (Phase 1)
  - ast_nodes.py           : Abstract Syntax Tree node classes (Phase 1)
  - parser.py              : Recursive-descent parser (tokens -> AST) (Phase 1)
  - semantic_analyzer.py   : Semantic analyzer & Symbol Tables (Phase 2)
  - timetable_generator.py : Constraint-aware generator & verifier (Phase 3)
"""

from .tokens import Token, TokenType
from .lexer import Lexer, LexicalError
from .ast_nodes import (
    Program,
    RoomDeclaration,
    InvigilatorDeclaration,
    GroupDeclaration,
    ExamDeclaration,
    format_ast,
)
from .parser import Parser, SyntaxAnalysisError
from .semantic_analyzer import (
    SemanticAnalyzer,
    SemanticAnalysisError,
    format_symbol_tables,
    AUTO_SLOT,
)
from .timetable_generator import (
    TimetableGenerator,
    TimetableGenerationError,
    Timetable,
    Assignment,
    format_timetable,
    format_timetable_by_slot,
    verify_timetable,
)

__all__ = [
    "Token",
    "TokenType",
    "Lexer",
    "LexicalError",
    "Program",
    "RoomDeclaration",
    "InvigilatorDeclaration",
    "GroupDeclaration",
    "ExamDeclaration",
    "format_ast",
    "Parser",
    "SyntaxAnalysisError",
    "SemanticAnalyzer",
    "SemanticAnalysisError",
    "format_symbol_tables",
    "AUTO_SLOT",
    "TimetableGenerator",
    "TimetableGenerationError",
    "Timetable",
    "Assignment",
    "format_timetable",
    "format_timetable_by_slot",
    "verify_timetable",
]
