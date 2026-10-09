"""
test_ir_generator.py
====================

Unit tests for the TimetableLang Intermediate Representation (IR) generator
(src/ir_generator.py) — Phase 2 Intermediate Code.

Tests:
  - Generation of Quadruples (Op, Arg1, Arg2, Result)
  - Generation of Linear Three-Address Code (TAC) instructions
  - Preservation of resource attributes and slot directives (fixed and AUTO)
  - Text formatting for Intermediate Code review demonstration
"""

import unittest

from src.lexer import Lexer
from src.parser import Parser
from src.ir_generator import IRGenerator, format_intermediate_code


def generate_ir(source: str):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse_program()
    ir_gen = IRGenerator(program)
    ir_gen.generate()
    return ir_gen


class TestIRGenerator(unittest.TestCase):

    def test_room_quadruple_and_tac(self):
        source = "room hall_a capacity 100;"
        ir = generate_ir(source)

        self.assertEqual(len(ir.instructions), 1)
        self.assertEqual(len(ir.quadruples), 1)

        q = ir.quadruples[0]
        self.assertEqual(q.op, "DECL_ROOM")
        self.assertEqual(q.arg1, 100)
        self.assertIsNone(q.arg2)
        self.assertEqual(q.result, "hall_a")

        tac = ir.instructions[0].to_tac()
        self.assertIn("hall_a = ALLOC_ROOM capacity=100", tac)

    def test_invigilator_and_group_generation(self):
        source = """
        invigilator prof_x;
        group cse_a size 75;
        """
        ir = generate_ir(source)
        self.assertEqual(len(ir.instructions), 2)

        q_invig = ir.quadruples[0]
        self.assertEqual(q_invig.op, "DECL_INVIG")
        self.assertEqual(q_invig.result, "prof_x")

        q_grp = ir.quadruples[1]
        self.assertEqual(q_grp.op, "DECL_GROUP")
        self.assertEqual(q_grp.arg1, 75)
        self.assertEqual(q_grp.result, "cse_a")

    def test_exam_schedule_tac_and_quadruple(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 80;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        exam CS102 room hall_a invigilator prof_x students cse_a slot 0;
        """
        ir = generate_ir(source)
        self.assertEqual(len(ir.instructions), 5)

        exam1_tac = ir.instructions[3].to_tac()
        self.assertIn("SCHEDULE CS101 -> room=hall_a, invig=prof_x, group=cse_a, slot=SLOT_1", exam1_tac)

        exam2_tac = ir.instructions[4].to_tac()
        self.assertIn("SCHEDULE CS102 -> room=hall_a, invig=prof_x, group=cse_a, slot=AUTO", exam2_tac)

    def test_format_intermediate_code(self):
        source = """
        room hall_a capacity 100;
        invigilator prof_x;
        group cse_a size 80;
        exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
        """
        ir = generate_ir(source)
        formatted = format_intermediate_code(ir)
        self.assertIn("Linear Three-Address Code (TAC):", formatted)
        self.assertIn("Quadruples (Op, Arg1, Arg2, Result):", formatted)
        self.assertIn("DECL_ROOM", formatted)
        self.assertIn("SCHED_EXAM", formatted)


if __name__ == "__main__":
    unittest.main()
