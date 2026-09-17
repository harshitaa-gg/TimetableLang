# TimetableLang — Phase 1 (Compiler Front End)

A Domain-Specific Language (DSL) and compiler pipeline for describing
and validating examination timetables. This repository contains the
**Phase 1** implementation: the compiler **front end** (lexer +
recursive-descent parser + AST).

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

## 3. Phase 1 Architecture

Phase 1 implements only the **compiler front end**:

```
TimetableLang Source File
        |
      Lexer            (src/lexer.py)
        |
   Token Stream        (src/tokens.py)
        |
      Parser           (src/parser.py)
        |
       AST             (src/ast_nodes.py)
        |
Syntax / Error Reporting
```

Phase 1 answers two questions:

1. **Lexical analysis**: "Can this text be broken into valid
   TimetableLang tokens?"
2. **Syntax analysis**: "Do those tokens follow the TimetableLang
   grammar, and can we build a structured AST from them?"

It does **not** answer "Is this timetable logically valid?" (are
rooms/invigilators/groups actually declared, is capacity enough, are
there scheduling conflicts?) — that is Phase 2 (semantic analysis),
and it does not generate a final timetable — that is Phase 3.

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

## 6. Project Structure

```
TimetableLang/
├── src/
│   ├── __init__.py
│   ├── tokens.py       # TokenType enum + Token class
│   ├── lexer.py        # Lexer: source code -> tokens
│   ├── ast_nodes.py    # AST node classes (Program, RoomDeclaration, ...)
│   └── parser.py       # Recursive-descent parser: tokens -> AST
│
├── examples/            # Sample .tt input files (see section 8)
├── tests/               # Unit tests for lexer and parser
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
5. Print `PHASE 1 RESULT: SUCCESS` or `PHASE 1 RESULT: FAILED`.

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
PHASE 1 RESULT: SUCCESS
```

The process exits with status code `0`.

## 10. Expected Behavior — Lexical Errors

For `lexical_invalid_character.tt`:

```
[1] LEXICAL ANALYSIS
    LEXICAL ANALYSIS: FAILED
    Lexical Error (line 1, column 22): Invalid character '@'

PHASE 1 RESULT: FAILED (lexical error)
```

The process exits with status code `1`. Syntax analysis is not
attempted when lexical analysis fails.

## 11. Expected Behavior — Syntax Errors

For example, for `syntax_missing_keyword.tt` (`room hall_a 100;`):

```
[1] LEXICAL ANALYSIS
    LEXICAL ANALYSIS: SUCCESS
    ...

[2] SYNTAX ANALYSIS
    SYNTAX ANALYSIS: FAILED
    Syntax Error (line 1, column 13): Expected keyword 'capacity' but found NUMBER '100'

PHASE 1 RESULT: FAILED (syntax error)
```

The parser stops gracefully with a descriptive message (including
line/column) rather than crashing with a raw Python traceback. The
process exits with status code `1`.

## 12. Running the Tests

```bash
python -m unittest discover -s tests -v
```

This runs 23 unit tests covering:
- Lexer: token classification, whitespace handling, empty input,
  invalid characters, line/column tracking.
- Parser: all four valid declaration types, multiple declarations,
  varied whitespace/newline formatting, an empty program, and all
  eight Phase 1 syntax error categories.

## 13. What Is Intentionally NOT Implemented Yet

The following are **Phase 2 / Phase 3** work and are **not** present
in this repository:

- Symbol tables
- Semantic analysis (checking that a referenced room, invigilator,
  or student group was actually declared)
- Room capacity validation
- Room double-booking detection
- Invigilator double-booking detection
- Student-group scheduling conflicts
- Timetable generation
- Any scheduling optimization, graph coloring, genetic algorithms,
  or AI/ML-based scheduling

These will be added in later phases, building on this front end
rather than replacing it.
