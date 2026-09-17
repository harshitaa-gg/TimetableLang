# Phase 2 Delivery — What To Do With These Files

This ZIP contains ONLY the files that are new or changed for Phase 2.
Everything from Phase 1 (lexer, parser, tokens, ast_nodes, test_lexer,
test_parser, README structure, requirements.txt, .gitignore) is
unchanged and NOT included here — keep your existing copies of those.

## NEW files — add these to your project as-is

    src/semantic_analyzer.py           -> put in TimetableLang/src/
    tests/test_semantic_analyzer.py    -> put in TimetableLang/tests/

    examples/semantic_duplicate_room.tt
    examples/semantic_duplicate_invigilator.tt
    examples/semantic_duplicate_group.tt
    examples/semantic_unknown_room.tt
    examples/semantic_unknown_invigilator.tt
    examples/semantic_unknown_group.tt
    examples/semantic_capacity_violation.tt
    examples/semantic_room_conflict.tt
    examples/semantic_invigilator_conflict.tt
    examples/semantic_group_conflict.tt
                                        -> put all 10 in TimetableLang/examples/

## UPDATED files — REPLACE your existing copies entirely

    main.py        -> replace TimetableLang/main.py completely.
                       (Phase 1 lexer/parser/AST steps [1]-[3] are
                       unchanged; a new step [4] SEMANTIC ANALYSIS was
                       added, and the final result line changed from
                       "PHASE 1 RESULT: ..." to "COMPILATION RESULT: ...".)

    README.md      -> replace TimetableLang/README.md completely.
                       (Documents Phase 2: symbol tables, the 10
                       semantic checks, updated example table, updated
                       expected-output sections, and updated test count
                       of 42.)

## Nothing else changes

    src/tokens.py, src/lexer.py, src/ast_nodes.py, src/parser.py,
    src/__init__.py, tests/test_lexer.py, tests/test_parser.py,
    tests/__init__.py, requirements.txt, .gitignore, valid_small.tt,
    valid_large.tt, and all existing lexical_*.tt / syntax_*.tt files
    are untouched.

## After copying everything in

Run from the project root:

    python -m unittest discover -s tests -v

You should see 42 tests, all passing (23 from Phase 1 + 19 new Phase 2
tests). Then try:

    python main.py examples/valid_small.tt
    python main.py examples/semantic_capacity_violation.tt
    python main.py examples/semantic_room_conflict.tt

to see Phase 2 semantic analysis succeed and fail as expected.
