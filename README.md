# TimetableLang — Complete Compiler Pipeline

A Domain-Specific Language (DSL) and compiler pipeline for describing, validating, and generating examination timetables.

- **Phase 1 (Frontend)**: Lexer + Recursive-Descent Parser + Abstract Syntax Tree (AST).
- **Phase 2 (Semantic Analysis)**: Symbol Tables + Semantic Validation (declarations, references, room capacities, resource conflicts).
- **Phase 3 (Generation & Verification)**: Constraint-Aware Timetable Generator (fixed slots, AUTO slot 0, backtracking, max-slots constraints) + Independent Timetable Verifier.

---

## 1. Project Purpose & Architecture

TimetableLang is a domain-specific language and compiler that translates a timetable specification into a valid examination timetable by performing lexical analysis, syntax analysis, semantic validation, and constraint-aware timetable generation.

```text
                    ┌──────────────────────────┐
                    │      TimetableLang       │
                    │       Source File        │
                    │        (.tt file)        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │      1. LEXER            │
                    │   Lexical Analysis       │
                    │                          │
                    │ .tt source → Tokens      │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │      2. PARSER           │
                    │   Syntax Analysis        │
                    │                          │
                    │ Tokens → Parse Structure │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       3. AST             │
                    │ Abstract Syntax Tree     │
                    │                          │
                    │ Structured representation│
                    │ of timetable program     │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  4. SEMANTIC ANALYZER   │
                    │                          │
                    │ • Declarations           │
                    │ • References             │
                    │ • Room capacity          │
                    │ • Duplicate declarations │
                    │ • Resource conflicts     │
                    └────────────┬─────────────┘
                                 │
                         Valid Program
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ 5. TIMETABLE GENERATOR  │
                    │                          │
                    │ • Fixed slots            │
                    │ • AUTO slots (slot 0)    │
                    │ • Resource constraints   │
                    │ • Capacity constraints   │
                    │ • Backtracking           │
                    │ • max-slots constraint   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ 6. TIMETABLE VERIFIER   │
                    │                          │
                    │ Independently verifies   │
                    │ the generated timetable  │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  7. FINAL TIMETABLE      │
                    │                          │
                    │ Course → Room            │
                    │         → Invigilator    │
                    │         → Student Group  │
                    │         → Time Slot      │
                    └──────────────────────────┘
```

---

## 2. Language Declarations

| Declaration   | Purpose                                   | Example |
|---------------|--------------------------------------------|---------|
| `room`        | Declares an exam room and its capacity     | `room hall_a capacity 100;` |
| `invigilator` | Declares an available invigilator          | `invigilator prof_x;` |
| `group`       | Declares a student group and its size      | `group cse_a size 80;` |
| `exam`        | Declares an exam and assigned resources    | `exam CS101 room hall_a invigilator prof_x students cse_a slot 1;` |

### Fixed vs Automatic Slots

- **Fixed Exam**: `slot 1`, `slot 2`, ... indicates a pinned slot. The generator honors and verifies this slot.
- **Automatic Exam (AUTO)**: `slot 0` indicates the author requests the compiler to automatically assign a valid, clash-free time slot.

---

## 3. Project Structure

```text
TimetableLang/
├── src/
│   ├── __init__.py
│   ├── tokens.py               # TokenType enum + Token class
│   ├── lexer.py                # Lexer: source code -> tokens (Phase 1)
│   ├── ast_nodes.py            # AST node classes (Program, RoomDeclaration, ...)
│   ├── parser.py               # Recursive-descent parser: tokens -> AST (Phase 1)
│   ├── semantic_analyzer.py    # Semantic analyzer & symbol tables (Phase 2)
│   └── timetable_generator.py  # Timetable generator & independent verifier (Phase 3)
│
├── examples/                   # Sample .tt input files (valid, syntax, semantic errors)
├── tests/                      # Unit & integration test suites (55 tests)
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_semantic_analyzer.py
│   └── test_timetable_generator.py
│
├── main.py                     # Compiler driver (Pipeline Stages 1 to 7)
├── README.md
└── requirements.txt
```

---

## 4. How to Run the Compiler

Requirements: **Python 3.8+** (standard library only).

### Basic Run
```bash
python main.py examples/valid_small.tt
```

### With AUTO Slots
```bash
python main.py examples/valid_auto.tt
```

### Limiting Maximum Slots
```bash
python main.py examples/valid_auto.tt --max-slots 2
```

---

## 5. Running the Test Suite

```bash
python -m unittest discover tests -v
```

All 55 unit and integration tests verify:
- **Lexer** (`test_lexer.py`): tokens, identifiers, keywords, position tracking, invalid chars.
- **Parser** (`test_parser.py`): valid grammars, syntax error reporting with exact line/column.
- **Semantic Analyzer** (`test_semantic_analyzer.py`): duplicate checks, undeclared references, capacity violations, resource double-booking.
- **Timetable Generator & Verifier** (`test_timetable_generator.py`): fixed slots, auto slot 0 assignment, backtracking resolution, slot limit enforcement, and independent conflict verification.
