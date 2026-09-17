#!/usr/bin/env python3
"""
main.py
=======

Main compiler driver for TimetableLang — PHASE 1 + PHASE 2 + PHASE 3.

Usage:
    python main.py <path-to-source-file>.tt [--max-slots N]

Options:
    --max-slots N   How many examination slots are available to the
                    timetable generator. If omitted, the generator uses
                    one slot per exam, which is the safe upper bound.
                    Lowering this is how you test the case where no
                    valid timetable exists.

Pipeline implemented:

    SOURCE FILE
       |
    LEXICAL ANALYSIS     (src/lexer.py)                -- Phase 1
       |
    TOKENS
       |
    SYNTAX ANALYSIS      (src/parser.py)               -- Phase 1
       |
    AST                  (src/ast_nodes.py)            -- Phase 1
       |
    SEMANTIC ANALYSIS    (src/semantic_analyzer.py)    -- Phase 2
       |
    SYMBOL TABLES + VALIDATION RESULT
       |
    TIMETABLE GENERATION (src/timetable_generator.py)  -- Phase 3
       |
    FINAL EXAMINATION TIMETABLE

Each phase is a gate: if a phase fails, the later phases are not
attempted, and the driver prints a single clear COMPILATION RESULT line.
"""

import sys

from src.lexer import Lexer, LexicalError
from src.parser import Parser, SyntaxAnalysisError
from src.ast_nodes import format_ast
from src.semantic_analyzer import (
    SemanticAnalyzer,
    SemanticAnalysisError,
    format_symbol_tables,
)
from src.timetable_generator import (
    TimetableGenerator,
    TimetableGenerationError,
    format_timetable,
    format_timetable_by_slot,
)


def run_compiler(source_path: str, max_slots: int = None) -> bool:
    """
    Runs the full Phase 1 + Phase 2 + Phase 3 pipeline (lexer -> parser ->
    AST -> semantic analyzer -> timetable generator) on the given source
    file and prints progress / results to the console.

    Args:
        source_path: path to the .tt source file.
        max_slots: optional limit on the number of examination slots the
            generator may use.

    Returns:
        True if the program compiled AND a valid timetable was generated.
        False otherwise.
    """
    print("=" * 60)
    print("TimetableLang Compiler - Phase 1 + Phase 2 + Phase 3")
    print("(Lexer + Parser + Semantic Analyzer + Timetable Generator)")
    print(f"Source file: {source_path}")
    if max_slots is not None:
        print(f"Available slots: {max_slots}")
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
        print("    LEXICAL ANALYSIS: FAILED")
        print(f"    {e}")
        print("\nCOMPILATION RESULT: FAILED (lexical error)")
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
        print("    SYNTAX ANALYSIS: FAILED")
        print(f"    {e}")
        print("\nCOMPILATION RESULT: FAILED (syntax error)")
        return False

    print("    SYNTAX ANALYSIS: SUCCESS")
    print(f"    {len(program.declarations)} declaration(s) parsed.")

    # --- Step 3: AST Construction / Display --------------------------------
    print("\n[3] ABSTRACT SYNTAX TREE")
    print(format_ast(program))

    # --- Step 4: Semantic Analysis (Phase 2) --------------------------------
    print("\n[4] SEMANTIC ANALYSIS")
    analyzer = SemanticAnalyzer(program)
    try:
        analyzer.analyze()
    except SemanticAnalysisError as e:
        print("    SEMANTIC ANALYSIS: FAILED")
        print(f"    {e}")
        print("\nCOMPILATION RESULT: FAILED (semantic error)")
        return False

    print("    SEMANTIC ANALYSIS: SUCCESS")
    print("\n    Symbol Tables:")
    for line in format_symbol_tables(analyzer).splitlines():
        print(f"      {line}")

    # --- Step 5: Timetable Generation (Phase 3) -----------------------------
    # Only reached when lexical, syntax and semantic analysis have all
    # succeeded. The generator reuses the analyzer's symbol tables; it does
    # not re-read the source, the tokens, or bypass validation.
    print("\n[5] TIMETABLE GENERATION")
    generator = TimetableGenerator(analyzer, max_slots=max_slots)
    try:
        timetable = generator.generate()
    except TimetableGenerationError as e:
        print("    TIMETABLE GENERATION: FAILED")
        for line in str(e).splitlines():
            print(f"    {line}")
        print("\nCOMPILATION RESULT: FAILED (timetable generation error)")
        return False

    print("    TIMETABLE GENERATION: SUCCESS")
    print(f"    {len(timetable.assignments)} exam(s) assigned.")

    # --- Step 6: Final Timetable -------------------------------------------
    print("\n[6] FINAL TIMETABLE\n")
    print(format_timetable(timetable))

    print("\n    Slot-by-slot view:")
    for line in format_timetable_by_slot(timetable).splitlines():
        print(f"      {line}")

    print("\n" + "=" * 60)
    print("COMPILATION RESULT: SUCCESS")
    print("Program successfully compiled and timetable generated.")
    print("=" * 60)
    return True


def parse_arguments(argv):
    """
    Very small hand-written argument parser, in keeping with the rest of the
    project (standard library only, nothing clever).

    Returns:
        (source_path, max_slots) on success, or None if the arguments were
        not understood.
    """
    source_path = None
    max_slots = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--max-slots":
            if i + 1 >= len(argv):
                print("ERROR: --max-slots requires a number.")
                return None
            value = argv[i + 1]
            if not value.isdigit() or int(value) < 1:
                print(f"ERROR: --max-slots must be a positive integer (got '{value}').")
                return None
            max_slots = int(value)
            i += 2
            continue
        if arg.startswith("--"):
            print(f"ERROR: Unknown option '{arg}'.")
            return None
        if source_path is not None:
            print("ERROR: More than one source file given.")
            return None
        source_path = arg
        i += 1

    if source_path is None:
        return None
    return source_path, max_slots


def main():
    parsed = parse_arguments(sys.argv[1:])
    if parsed is None:
        print("Usage: python main.py <path-to-source-file>.tt [--max-slots N]")
        sys.exit(1)

    source_path, max_slots = parsed
    success = run_compiler(source_path, max_slots=max_slots)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
