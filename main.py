#!/usr/bin/env python3
"""
main.py
=======

Main compiler driver for TimetableLang — PHASE 1 ONLY.

Usage:
    python main.py <path-to-source-file>.tt

Pipeline implemented (Phase 1 front end only):

    SOURCE FILE
       |
    LEXICAL ANALYSIS   (src/lexer.py)
       |
    TOKENS
       |
    SYNTAX ANALYSIS    (src/parser.py)
       |
    AST                (src/ast_nodes.py)
       |
    PHASE 1 SUCCESS

Semantic analysis, symbol tables, conflict detection, and timetable
generation are Phase 2 / Phase 3 work and are intentionally NOT
performed by this driver.
"""

import sys

from src.lexer import Lexer, LexicalError
from src.parser import Parser, SyntaxAnalysisError
from src.ast_nodes import format_ast


def run_phase1(source_path: str) -> bool:
    """
    Runs the Phase 1 pipeline (lexer -> parser -> AST) on the given
    source file and prints progress/results to the console.

    Returns:
        True if Phase 1 completed successfully, False otherwise.
    """
    print("=" * 60)
    print(f"TimetableLang Compiler - Phase 1 (Lexer + Parser)")
    print(f"Source file: {source_path}")
    print("=" * 60)

    # --- Step 0: Read the source file -----------------------------------
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()
    except OSError as e:
        print(f"\nERROR: Could not read source file '{source_path}': {e}")
        return False

    # --- Step 1: Lexical Analysis ----------------------------------------
    print("\n[1] LEXICAL ANALYSIS")
    try:
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
    except LexicalError as e:
        print(f"    LEXICAL ANALYSIS: FAILED")
        print(f"    {e}")
        print("\nPHASE 1 RESULT: FAILED (lexical error)")
        return False

    print("    LEXICAL ANALYSIS: SUCCESS")
    print(f"    {len(tokens)} tokens produced (including EOF).")
    print("\n    Token Stream:")
    for tok in tokens:
        print(f"      {tok}")

    # --- Step 2: Syntax Analysis ------------------------------------------
    print("\n[2] SYNTAX ANALYSIS")
    try:
        parser = Parser(tokens)
        program = parser.parse_program()
    except SyntaxAnalysisError as e:
        print(f"    SYNTAX ANALYSIS: FAILED")
        print(f"    {e}")
        print("\nPHASE 1 RESULT: FAILED (syntax error)")
        return False

    print("    SYNTAX ANALYSIS: SUCCESS")
    print(f"    {len(program.declarations)} declaration(s) parsed.")

    # --- Step 3: AST Construction / Display --------------------------------
    print("\n[3] ABSTRACT SYNTAX TREE")
    print(format_ast(program))

    print("\n" + "=" * 60)
    print("PHASE 1 RESULT: SUCCESS")
    print("(Lexical analysis and syntax analysis both completed")
    print(" successfully. Semantic analysis and timetable generation")
    print(" are Phase 2 / Phase 3 and are not performed here.)")
    print("=" * 60)
    return True


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path-to-source-file>.tt")
        sys.exit(1)

    source_path = sys.argv[1]
    success = run_phase1(source_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
