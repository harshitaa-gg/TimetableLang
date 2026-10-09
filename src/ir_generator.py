"""
ir_generator.py
===============

Intermediate Representation (IR) Generator for TimetableLang — PHASE 2.

Translates the semantically validated AST / Symbol Tables into a linearized
Intermediate Code format:
  1. Quadruples: (Operator, Argument 1, Argument 2, Result)
  2. Three-Address Code (TAC) Instructions: Human-readable linearized representation.

In compiler architecture, this decoupling ensures that the backend
execution engine (Timetable Generator) operates upon an abstract intermediate
instruction stream rather than directly coupling to the frontend AST nodes.

IR Instruction Operations:
  - DECL_ROOM:  allocates room with capacity
  - DECL_INVIG: allocates invigilator resource
  - DECL_GROUP: allocates student group with size
  - SCHED_EXAM: schedules exam with resource bindings and slot specification
"""

from dataclasses import dataclass
from typing import Any, List, Optional
from .ast_nodes import (
    Program,
    RoomDeclaration,
    InvigilatorDeclaration,
    GroupDeclaration,
    ExamDeclaration,
)


@dataclass
class Quadruple:
    """
    Standard compiler Quadruple representation:
    (Op, Arg1, Arg2, Result)
    """
    op: str
    arg1: Optional[Any] = None
    arg2: Optional[Any] = None
    result: Optional[Any] = None

    def __str__(self) -> str:
        a1 = str(self.arg1) if self.arg1 is not None else "-"
        a2 = str(self.arg2) if self.arg2 is not None else "-"
        res = str(self.result) if self.result is not None else "-"
        return f"({self.op:<12}, {a1:<12}, {a2:<12}, {res})"


@dataclass
class IRInstruction:
    """
    Three-Address Code (TAC) style linearized instruction.
    """
    op: str
    target: str
    args: List[str]

    def to_tac(self) -> str:
        """Formatted Three-Address Code string."""
        if self.op == "DECL_ROOM":
            return f"{self.target} = ALLOC_ROOM capacity={self.args[0]}"
        elif self.op == "DECL_INVIG":
            return f"{self.target} = ALLOC_INVIGILATOR"
        elif self.op == "DECL_GROUP":
            return f"{self.target} = ALLOC_GROUP size={self.args[0]}"
        elif self.op == "SCHED_EXAM":
            room, invig, grp, slot = self.args
            slot_str = "AUTO" if slot == "0" else f"SLOT_{slot}"
            return f"SCHEDULE {self.target} -> room={room}, invig={invig}, group={grp}, slot={slot_str}"
        return f"{self.op} {self.target} {', '.join(self.args)}"


class IRGenerator:
    """
    Intermediate Code Generator.
    Walks the validated AST and generates both Quadruples and TAC instructions.
    """

    def __init__(self, program: Program):
        self.program = program
        self.quadruples: List[Quadruple] = []
        self.instructions: List[IRInstruction] = []

    def generate(self) -> List[IRInstruction]:
        """
        Generate intermediate code from declarations.
        """
        self.quadruples.clear()
        self.instructions.clear()

        for decl in self.program.declarations:
            if isinstance(decl, RoomDeclaration):
                self._gen_room(decl)
            elif isinstance(decl, InvigilatorDeclaration):
                self._gen_invigilator(decl)
            elif isinstance(decl, GroupDeclaration):
                self._gen_group(decl)
            elif isinstance(decl, ExamDeclaration):
                self._gen_exam(decl)

        return self.instructions

    def _gen_room(self, decl: RoomDeclaration):
        self.quadruples.append(
            Quadruple(op="DECL_ROOM", arg1=decl.capacity, arg2=None, result=decl.name)
        )
        self.instructions.append(
            IRInstruction(op="DECL_ROOM", target=decl.name, args=[str(decl.capacity)])
        )

    def _gen_invigilator(self, decl: InvigilatorDeclaration):
        self.quadruples.append(
            Quadruple(op="DECL_INVIG", arg1=None, arg2=None, result=decl.name)
        )
        self.instructions.append(
            IRInstruction(op="DECL_INVIG", target=decl.name, args=[])
        )

    def _gen_group(self, decl: GroupDeclaration):
        self.quadruples.append(
            Quadruple(op="DECL_GROUP", arg1=decl.size, arg2=None, result=decl.name)
        )
        self.instructions.append(
            IRInstruction(op="DECL_GROUP", target=decl.name, args=[str(decl.size)])
        )

    def _gen_exam(self, decl: ExamDeclaration):
        args_quad = f"{decl.room}:{decl.invigilator}"
        res_quad = f"{decl.students}:slot{decl.slot}"
        self.quadruples.append(
            Quadruple(op="SCHED_EXAM", arg1=args_quad, arg2=res_quad, result=decl.course)
        )
        self.instructions.append(
            IRInstruction(
                op="SCHED_EXAM",
                target=decl.course,
                args=[decl.room, decl.invigilator, decl.students, str(decl.slot)],
            )
        )


def format_intermediate_code(ir_gen: IRGenerator) -> str:
    """
    Pretty-print the Intermediate Representation (TAC and Quadruples)
    for compiler review demonstration.
    """
    lines = []
    lines.append("Linear Three-Address Code (TAC):")
    lines.append("-" * 55)
    for i, instr in enumerate(ir_gen.instructions, 1):
        lines.append(f"  {i:02d}: {instr.to_tac()}")

    lines.append("")
    lines.append("Quadruples (Op, Arg1, Arg2, Result):")
    lines.append("-" * 55)
    lines.append(f"  {'#':<4} {'(Op':<14} {'Arg1':<14} {'Arg2':<14} {'Result)'}")
    lines.append("  " + "-" * 51)
    for i, q in enumerate(ir_gen.quadruples, 1):
        lines.append(f"  {i:02d}: {q}")

    return "\n".join(lines)
