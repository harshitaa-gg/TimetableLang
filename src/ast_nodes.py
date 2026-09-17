"""
ast_nodes.py
============

Abstract Syntax Tree (AST) node classes for TimetableLang.

The AST represents the LOGICAL structure of a TimetableLang program,
as opposed to the flat token stream produced by the lexer. Each class
here corresponds directly to one grammar rule from the project's
formal grammar (see the project document, section 12).

Note: this file is named "ast_nodes.py" (not "ast.py") purely to avoid
any confusion with Python's own built-in "ast" standard library module
when reading import statements; it plays exactly the role of the
"ast.py" described in the project design.

Node classes:
    Program
    RoomDeclaration
    InvigilatorDeclaration
    GroupDeclaration
    ExamDeclaration
"""


class Program:
    """
    The root AST node.

    Attributes:
        declarations (list): a list of declaration nodes, in the order
            they appeared in the source file. Each element is one of
            RoomDeclaration, InvigilatorDeclaration, GroupDeclaration,
            or ExamDeclaration.
    """

    def __init__(self, declarations):
        self.declarations = declarations

    def __repr__(self):
        return f"Program(declarations={self.declarations!r})"


class RoomDeclaration:
    """AST node for: room <name> capacity <number>;"""

    def __init__(self, name, capacity, line=None, column=None):
        self.name = name
        self.capacity = capacity
        self.line = line
        self.column = column

    def __repr__(self):
        return f"RoomDeclaration(name={self.name!r}, capacity={self.capacity!r})"


class InvigilatorDeclaration:
    """AST node for: invigilator <name>;"""

    def __init__(self, name, line=None, column=None):
        self.name = name
        self.line = line
        self.column = column

    def __repr__(self):
        return f"InvigilatorDeclaration(name={self.name!r})"


class GroupDeclaration:
    """AST node for: group <name> size <number>;"""

    def __init__(self, name, size, line=None, column=None):
        self.name = name
        self.size = size
        self.line = line
        self.column = column

    def __repr__(self):
        return f"GroupDeclaration(name={self.name!r}, size={self.size!r})"


class ExamDeclaration:
    """
    AST node for:
        exam <course>
         room <room>
         invigilator <invigilator>
         students <group>
         slot <number>;
    """

    def __init__(self, course, room, invigilator, students, slot, line=None, column=None):
        self.course = course
        self.room = room
        self.invigilator = invigilator
        self.students = students
        self.slot = slot
        self.line = line
        self.column = column

    def __repr__(self):
        return (
            f"ExamDeclaration(course={self.course!r}, room={self.room!r}, "
            f"invigilator={self.invigilator!r}, students={self.students!r}, "
            f"slot={self.slot!r})"
        )


# ----------------------------------------------------------------------
# Pretty-printing helper
# ----------------------------------------------------------------------
#
# This is purely a display convenience for demonstrating that the AST
# has real structure (not just a token list). It is not part of the
# grammar itself.

def format_ast(program: Program) -> str:
    """Render a Program AST as an indented tree, similar to the example
    in the project document (section 15)."""

    lines = ["Program"]
    decls = program.declarations
    for i, decl in enumerate(decls):
        is_last_decl = i == len(decls) - 1
        branch = "└──" if is_last_decl else "├──"
        lines.append(f" {branch} {type(decl).__name__}")
        child_prefix = "     " if is_last_decl else " │   "

        fields = _fields_for(decl)
        for j, (field_name, field_value) in enumerate(fields):
            is_last_field = j == len(fields) - 1
            field_branch = "└──" if is_last_field else "├──"
            lines.append(f"{child_prefix}{field_branch} {field_name}: {field_value}")

    return "\n".join(lines)


def _fields_for(decl):
    """Return an ordered list of (label, value) pairs for a declaration
    node, used only for pretty-printing the AST."""

    if isinstance(decl, RoomDeclaration):
        return [("Name", decl.name), ("Capacity", decl.capacity)]
    if isinstance(decl, InvigilatorDeclaration):
        return [("Name", decl.name)]
    if isinstance(decl, GroupDeclaration):
        return [("Name", decl.name), ("Size", decl.size)]
    if isinstance(decl, ExamDeclaration):
        return [
            ("Course", decl.course),
            ("Room", decl.room),
            ("Invigilator", decl.invigilator),
            ("Students", decl.students),
            ("Slot", decl.slot),
        ]
    return []
