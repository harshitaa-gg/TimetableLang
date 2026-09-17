#!/usr/bin/env python3
"""
main.py
=======

Main compiler driver for TimetableLang:
  Phase 1 (Lexer + Parser + AST)
  Phase 2 (Semantic Analyzer + Symbol Tables)
  Phase 3 (Constraint-Aware Timetable Generator + Independent Verifier)

Usage:
    python main.py <path-to-source-file>.tt [--max-slots N]

Options:
    --max-slots N   How many examination slots are available to the
                    timetable generator. If omitted, the generator uses
                    one slot per exam, which is the safe upper bound.
                    Lowering this is how you test the case where no
                    valid timetable exists.

Architecture & Pipeline:

    SOURCE FILE (.tt)
           │
           ▼
    [1] LEXICAL ANALYSIS     (src/lexer.py)              -- Phase 1
           │ Tokens
           ▼
    [2] SYNTAX ANALYSIS      (src/parser.py)             -- Phase 1
           │ Parse Tree / Nodes
           ▼
    [3] ABSTRACT SYNTAX TREE (src/ast_nodes.py)          -- Phase 1
           │ AST Representation
           ▼
    [4] SEMANTIC ANALYSIS    (src/semantic_analyzer.py)  -- Phase 2
           │ Validated AST + Symbol Tables
           ▼
    [5] TIMETABLE GENERATOR  (src/timetable_generator.py)-- Phase 3
           │ Generated Timetable (Backtracking + Constraints)
           ▼
    [6] TIMETABLE VERIFIER   (src/timetable_generator.py)-- Phase 3
           │ Independent Conflict & Constraint Verification
           ▼
    [7] FINAL EXAMINATION TIMETABLE

Each phase serves as a strict gate: if any phase fails, compilation aborts
immediately with a descriptive error message.
"""

import sys

# Ensure UTF-8 output encoding across Windows / different terminal environments
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
    verify_timetable,
)


def run_compiler(source_path: str, max_slots: int = None) -> bool:
    """
    Runs the complete 6-stage compiler pipeline on the given source file
    and prints progress and results to the console.

    Args:
        source_path: path to the .tt source file.
        max_slots: optional limit on the number of examination slots the
            generator may use.

    Returns:
        True if the program compiled, generated a timetable, and passed
        independent verification. False otherwise.
    """
    print("=" * 60)
    print("TimetableLang Compiler Pipeline")
    print("Lexer -> Parser -> AST -> Semantic Analyzer -> Generator -> Verifier")
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
    print(f"    {len(timetable.assignments)} exam(s) assigned across {len(timetable.slots_used())} slot(s).")

    # --- Step 6: Independent Timetable Verification -----------------------
    print("\n[6] TIMETABLE VERIFICATION")
    violations = verify_timetable(timetable, analyzer=analyzer, max_slots=max_slots)
    if violations:
        print("    TIMETABLE VERIFICATION: FAILED")
        for v in violations:
            print(f"    - {v}")
        print("\nCOMPILATION RESULT: FAILED (timetable verification error)")
        return False

    print("    TIMETABLE VERIFICATION: SUCCESS (0 conflicts or violations detected)")

    # --- Step 7: Final Timetable Output ------------------------------------
    print("\n[7] FINAL EXAMINATION TIMETABLE\n")
    print(format_timetable(timetable))

    print("\n    Slot-by-slot view:")
    for line in format_timetable_by_slot(timetable).splitlines():
        print(f"      {line}")

    print("\n" + "=" * 60)
    print("COMPILATION RESULT: SUCCESS")
    print("Program successfully compiled and verified timetable generated.")
    print("=" * 60)
    return True


def parse_arguments(argv):
    """
    Small hand-written argument parser.

    Returns:
        (source_path, max_slots) on success, or None on syntax error.
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
