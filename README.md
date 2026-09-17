# TimetableLang — Phase 1 + Phase 2

A Domain-Specific Language (DSL) and compiler pipeline for describing
and validating examination timetables. This repository currently
contains:

- **Phase 1**: the compiler **front end** (lexer + recursive-descent
  parser + AST).
- **Phase 2**: **semantic analysis** (symbol tables + validation of
  duplicate declarations, undeclared references, room capacity, and
  scheduling conflicts).

Timetable generation (Phase 3) is not implemented yet.

## 1. Project Purpose

Preparing examination timetables by hand can lead to room
double-booking, invigilator conflicts, student clashes, and
capacity problems. TimetableLang is a small, purpose-built language
for describing rooms, invigilators, student groups, and exams in a
structured, machine-checkable way, and applies Compiler Design
concepts (lexical analysis, syntax analysis, AST construction,
and — in later phases — semantic analysis) to detect problems
automatically.

This project is a Compiler Design Lab / academic project. It is
**not** intended to be a general-purpose programming language or a
full scheduling optimizer (no graph coloring, genetic algorithms, or
AI-based optimization).

## 2. What TimetableLang Is

TimetableLang currently supports four declaration types:

| Declaration   | Purpose                                   |
|---------------|--------------------------------------------|
| `room`        | Declares an exam room and its capacity     |
| `invigilator` | Declares an available invigilator          |
| `group`       | Declares a student group and its size      |
| `exam`        | Schedules a course into a room/slot/etc.   |

## 3. Architecture (Phase 1 + Phase 2)

```
TimetableLang Source File
        |
      Lexer                  (src/lexer.py)              -- Phase 1
        |
   Token Stream              (src/tokens.py)
        |
      Parser                 (src/parser.py)              -- Phase 1
        |
       AST                   (src/ast_nodes.py)           -- Phase 1
        |
  Semantic Analyzer          (src/semantic_analyzer.py)   -- Phase 2
        |
  Symbol Tables + Validation Result
```

Three questions are answered, in order, and each is intentionally
kept separate:

1. **Lexical analysis** (Phase 1): "Can this text be broken into
   valid TimetableLang tokens?"
2. **Syntax analysis** (Phase 1): "Do those tokens follow the
   TimetableLang grammar, and can we build a structured AST from
   them?"
3. **Semantic analysis** (Phase 2): "Is this syntactically valid
   program logically meaningful?" — are all referenced rooms,
   invigilators, and student groups actually declared, is room
   capacity sufficient, and are there no double-bookings?

It does **not** generate a final timetable — that is Phase 3, and is
not implemented yet.

## 4. Supported Syntax

```
room hall_a capacity 100;

invigilator prof_x;

group cse_a size 80;

exam CS101
 room hall_a
 invigilator prof_x
 students cse_a
 slot 1;
```

Keywords: `room`, `capacity`, `invigilator`, `group`, `size`, `exam`,
`students`, `slot`.

Identifiers: start with a letter or underscore, followed by letters,
digits, or underscores (e.g. `hall_a`, `prof_x`, `CS101`).

Numbers: non-negative integers (e.g. `1`, `80`, `100`).

Whitespace (spaces, tabs, newlines) and line breaks between an
`exam`'s fields are ignored — declarations can be written on one
line or spread across several, as in the example above.

## 5. Grammar

```
Program            -> DeclarationList

DeclarationList    -> Declaration DeclarationList
                    | epsilon

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
```

This is implemented as a **recursive-descent parser**: each grammar
rule is one Python method in `src/parser.py`, and the methods call
each other in the same shape as the grammar above.

## 5a. Phase 2 — Semantic Analysis

Once the parser has produced a syntactically valid AST,
`src/semantic_analyzer.py` walks it and checks whether the program
actually makes sense. It works **only on the AST** — it never
re-reads source text or tokens.

**Symbol tables.** Three plain Python dictionaries are built by
walking the declarations in source order:

```python
self.rooms = {}          # name -> RoomDeclaration
self.invigilators = {}   # name -> InvigilatorDeclaration
self.groups = {}         # name -> GroupDeclaration
self.exams = []          # ExamDeclaration objects, in source order
```

**Checks performed, in order, for every exam (stopping at the first
problem found, the same way the lexer and parser do):**

1. **Duplicate declarations** — a room, invigilator, or group name
   that appears twice is rejected the moment the second declaration
   is seen.
2. **Undeclared references** — every exam's `room`, `invigilator`,
   and `students` must name something that was actually declared.
3. **Room capacity** — the assigned group's size must not exceed the
   assigned room's capacity.
4. **Room conflict** — no room may be booked by two exams in the
   same slot.
5. **Invigilator conflict** — no invigilator may be assigned to two
   exams in the same slot.
6. **Group conflict** — no student group may have two exams in the
   same slot.

Each failure raises a `SemanticAnalysisError` carrying a `category`
(e.g. `"Capacity Violation"`, `"Room Conflict"`) and, where
available, the `line`/`column` of the offending declaration (reusing
the location information already stored on the AST nodes — no new
tracking is needed).

Phase 2 does **not** generate a timetable; it only validates. Nothing
here performs scheduling, optimization, or conflict *resolution* —
only conflict *detection*.

## 6. Project Structure

```
TimetableLang/
├── src/
│   ├── __init__.py
│   ├── tokens.py               # TokenType enum + Token class
│   ├── lexer.py                # Lexer: source code -> tokens
│   ├── ast_nodes.py            # AST node classes (Program, RoomDeclaration, ...)
│   ├── parser.py                # Recursive-descent parser: tokens -> AST
│   └── semantic_analyzer.py    # Semantic analyzer: AST -> symbol tables + validation (Phase 2)
│
├── examples/            # Sample .tt input files (see section 8)
├── tests/               # Unit tests for lexer, parser, and semantic analyzer
│
├── main.py              # Compiler driver / entry point
├── README.md
├── requirements.txt
└── .gitignore
```

> Note: the AST module is named `ast_nodes.py` rather than `ast.py`
> purely to avoid any confusion with Python's own built-in `ast`
> standard library module. It plays exactly the role described as
> `ast.py` in the project design document.

## 7. How to Run the Compiler

Requirements: **Python 3.8+**, standard library only (see
`requirements.txt` — no third-party packages needed).

From the project root:

```bash
python main.py examples/valid_small.tt
```

The driver will:
1. Read the source file.
2. Run lexical analysis and print the token stream (or a lexical
   error).
3. If lexical analysis succeeds, run syntax analysis and build the
   AST (or print a syntax error).
4. Print the AST in a readable tree form.
5. If syntax analysis succeeds, run semantic analysis: build the
   symbol tables and validate every exam (or print a semantic
   error).
6. Print the symbol tables in a readable form.
7. Print `COMPILATION RESULT: SUCCESS` or
   `COMPILATION RESULT: FAILED (... error)`.

## 8. Example Input Files

All example files are in `examples/`:

| File                                | Purpose                                        |
|--------------------------------------|-------------------------------------------------|
| `valid_small.tt`                     | A small, easy-to-inspect valid program          |
| `valid_large.tt`                     | A larger valid program (4 rooms, 4 invigilators, 5 groups, 7 exams) |
| `lexical_invalid_character.tt`       | Invalid character (`@`) — lexical error         |
| `syntax_missing_keyword.tt`          | Missing `capacity` keyword                      |
| `syntax_missing_identifier.tt`       | Missing room name identifier                    |
| `syntax_missing_number.tt`           | Missing capacity number                         |
| `syntax_missing_semicolon.tt`        | Missing terminating `;`                         |
| `syntax_wrong_order.tt`              | Fields written in the wrong order               |
| `syntax_missing_exam_field.tt`       | An `exam` declaration missing the `students` field |
| `syntax_unexpected_token.tt`         | An unexpected identifier (`professor`) where a keyword was expected |
| `semantic_duplicate_room.tt`         | `hall_a` declared twice                          |
| `semantic_duplicate_invigilator.tt`  | `prof_x` declared twice                          |
| `semantic_duplicate_group.tt`        | `cse_a` declared twice                           |
| `semantic_unknown_room.tt`           | Exam references a room that was never declared   |
| `semantic_unknown_invigilator.tt`    | Exam references an invigilator that was never declared |
| `semantic_unknown_group.tt`          | Exam references a student group that was never declared |
| `semantic_capacity_violation.tt`     | Group size (80) exceeds room capacity (50)       |
| `semantic_room_conflict.tt`          | Two exams booked into the same room in the same slot |
| `semantic_invigilator_conflict.tt`   | One invigilator assigned to two exams in the same slot |
| `semantic_group_conflict.tt`         | One student group has two exams in the same slot |

Run any of them the same way, for example:

```bash
python main.py examples/syntax_missing_keyword.tt
```

## 9. Expected Behavior — Valid Input

For `valid_small.tt` and `valid_large.tt`, you will see:

```
LEXICAL ANALYSIS: SUCCESS
...
SYNTAX ANALYSIS: SUCCESS
...
[3] ABSTRACT SYNTAX TREE
Program
 ├── RoomDeclaration
 │   ├── Name: hall_a
 │   └── Capacity: 100
 ...
[4] SEMANTIC ANALYSIS
    SEMANTIC ANALYSIS: SUCCESS

    Symbol Tables:
      Rooms:
        hall_a -> capacity 100
      Invigilators:
        prof_x
      Student Groups:
        cse_a -> size 80
      Exams:
        CS101: room=hall_a, invigilator=prof_x, students=cse_a, slot=1

COMPILATION RESULT: SUCCESS
Program is lexically, syntactically, and semantically valid.
```

The process exits with status code `0`.

## 10. Expected Behavior — Lexical Errors

For `lexical_invalid_character.tt`:

```
[1] LEXICAL ANALYSIS
    LEXICAL ANALYSIS: FAILED
    Lexical Error (line 1, column 22): Invalid character '@'

COMPILATION RESULT: FAILED (lexical error)
```

The process exits with status code `1`. Syntax and semantic analysis
are not attempted when lexical analysis fails.

## 11. Expected Behavior — Syntax Errors

For example, for `syntax_missing_keyword.tt` (`room hall_a 100;`):

```
[1] LEXICAL ANALYSIS
    LEXICAL ANALYSIS: SUCCESS
    ...

[2] SYNTAX ANALYSIS
    SYNTAX ANALYSIS: FAILED
    Syntax Error (line 1, column 13): Expected keyword 'capacity' but found NUMBER '100'

COMPILATION RESULT: FAILED (syntax error)
```

The parser stops gracefully with a descriptive message (including
line/column) rather than crashing with a raw Python traceback. The
process exits with status code `1`. Semantic analysis is not
attempted when syntax analysis fails.

## 11a. Expected Behavior — Semantic Errors (Phase 2)

For example, for `semantic_capacity_violation.tt`:

```
[1] LEXICAL ANALYSIS
    LEXICAL ANALYSIS: SUCCESS
    ...

[2] SYNTAX ANALYSIS
    SYNTAX ANALYSIS: SUCCESS
    ...

[3] ABSTRACT SYNTAX TREE
    ...

[4] SEMANTIC ANALYSIS
    SEMANTIC ANALYSIS: FAILED
    Semantic Error [Capacity Violation] (line 6, column 1): Room 'hall_a' has capacity 50, but group 'cse_a' has 80 students.

COMPILATION RESULT: FAILED (semantic error)
```

Every semantic error message names its **category** in brackets
(`Duplicate Declaration`, `Undeclared Reference`,
`Capacity Violation`, `Room Conflict`, `Invigilator Conflict`, or
`Group Conflict`) together with the line/column of the declaration
that triggered it, and the process exits with status code `1`.

## 12. Running the Tests

```bash
python -m unittest discover -s tests -v
```

This runs **42 unit tests** covering:
- **Lexer** (`test_lexer.py`): token classification, whitespace
  handling, empty input, invalid characters, line/column tracking.
- **Parser** (`test_parser.py`): all four valid declaration types,
  multiple declarations, varied whitespace/newline formatting, an
  empty program, and all eight Phase 1 syntax error categories.
- **Semantic analyzer** (`test_semantic_analyzer.py`): valid
  programs (including running the actual `valid_small.tt` and
  `valid_large.tt` files through the analyzer), all three duplicate
  declaration checks, all three undeclared reference checks, the
  capacity check (including the boundary case where size == capacity,
  which is allowed), and all three conflict checks — each verified
  both with small inline source snippets and by running the matching
  `examples/semantic_*.tt` file through the full pipeline.

To run only the semantic analyzer tests:

```bash
python -m unittest tests.test_semantic_analyzer -v
```

## 13. What Is Intentionally NOT Implemented Yet

The following are **Phase 3 (and beyond)** work and are **not**
present in this repository:

- Timetable generation (producing a final structured schedule)
- Any scheduling optimization, graph coloring, genetic algorithms,
  or AI/ML-based scheduling
- A web frontend, API server, database, or user accounts (a possible
  future architecture is `React -> FastAPI -> TimetableLang Compiler`,
  but none of that is built yet — this remains a command-line tool)

Phase 1 (lexer, parser, AST) and Phase 2 (symbol tables and semantic
validation: duplicate declarations, undeclared references, room
capacity, room/invigilator/group conflicts) are both implemented, as
described above.
