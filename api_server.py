"""
api_server.py
=============

Lightweight HTTP API server and Vercel serverless function entrypoint
for TimetableLang compiler execution.

Endpoints:
    POST /api/compile
        Request body: {"source": "<code string>", "max_slots": Optional[int]}
        Response body: {
            "success": bool,
            "stage_failed": Optional[str],
            "error": Optional[dict],
            "stages": {
                "lexer": {"status": str, "token_count": int, "tokens": list},
                "parser": {"status": str, "declaration_count": int},
                "ast": {"status": str, "tree": str},
                "semantic": {"status": str, "symbol_tables": str},
                "ir": {"status": str, "tac": list, "quadruples": list},
                "generator": {"status": str, "assignments_count": int, "slots_used": int},
                "verifier": {"status": str, "violations": list},
                "timetable": {"formatted": str, "by_slot": str, "assignments": list}
            }
        }

Can be run locally:
    python api_server.py [--port 8000]
Or used in Vercel Python runtime as a handler.
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

from src.lexer import Lexer, LexicalError
from src.parser import Parser, SyntaxAnalysisError
from src.ast_nodes import format_ast
from src.semantic_analyzer import (
    SemanticAnalyzer,
    SemanticAnalysisError,
    format_symbol_tables,
)
from src.ir_generator import IRGenerator
from src.timetable_generator import (
    TimetableGenerator,
    TimetableGenerationError,
    format_timetable,
    format_timetable_by_slot,
    verify_timetable,
)


def compile_timetable_source(source: str, max_slots: Optional[int] = None) -> Dict[str, Any]:
    """
    Executes all stages of the TimetableLang compiler pipeline and returns
    structured JSON-serializable results for every stage.
    """
    result: Dict[str, Any] = {
        "success": False,
        "stage_failed": None,
        "error": None,
        "stages": {
            "lexer": {"status": "pending"},
            "parser": {"status": "pending"},
            "ast": {"status": "pending"},
            "semantic": {"status": "pending"},
            "ir": {"status": "pending"},
            "generator": {"status": "pending"},
            "verifier": {"status": "pending"},
            "timetable": None,
        },
    }

    # 1. Lexical Analysis
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        token_list = [
            {
                "type": t.type.name,
                "value": str(t.value) if t.value is not None else None,
                "line": t.line,
                "column": t.column,
            }
            for t in tokens
        ]
        result["stages"]["lexer"] = {
            "status": "passed",
            "token_count": len(tokens),
            "tokens": token_list,
        }
    except LexicalError as e:
        result["stage_failed"] = "lexer"
        result["error"] = {
            "category": "Lexical Error",
            "message": str(e),
            "line": getattr(e, "line", None),
            "column": getattr(e, "column", None),
        }
        result["stages"]["lexer"] = {"status": "failed", "error": str(e)}
        return result

    # 2. Syntax Analysis & 3. AST
    try:
        parser = Parser(tokens)
        program = parser.parse_program()
        result["stages"]["parser"] = {
            "status": "passed",
            "declaration_count": len(program.declarations),
        }
        result["stages"]["ast"] = {
            "status": "passed",
            "tree": format_ast(program),
        }
    except SyntaxAnalysisError as e:
        result["stage_failed"] = "parser"
        result["error"] = {
            "category": "Syntax Error",
            "message": str(e),
            "line": getattr(e, "line", None),
            "column": getattr(e, "column", None),
        }
        result["stages"]["parser"] = {"status": "failed", "error": str(e)}
        return result

    # 4. Semantic Analysis & Symbol Tables
    analyzer = SemanticAnalyzer(program)
    try:
        analyzer.analyze()
        result["stages"]["semantic"] = {
            "status": "passed",
            "symbol_tables": format_symbol_tables(analyzer),
        }
    except SemanticAnalysisError as e:
        result["stage_failed"] = "semantic"
        result["error"] = {
            "category": getattr(e, "category", "Semantic Error"),
            "message": str(e),
            "line": getattr(e, "line", None),
            "column": getattr(e, "column", None),
        }
        result["stages"]["semantic"] = {"status": "failed", "error": str(e)}
        return result

    # 5. Intermediate Code (IR)
    ir_gen = IRGenerator(program)
    ir_gen.generate()
    result["stages"]["ir"] = {
        "status": "passed",
        "tac": [f"{i+1:02d}: {instr.to_tac()}" for i, instr in enumerate(ir_gen.instructions)],
        "quadruples": [
            {
                "index": i + 1,
                "op": q.op,
                "arg1": str(q.arg1) if q.arg1 is not None else "-",
                "arg2": str(q.arg2) if q.arg2 is not None else "-",
                "result": str(q.result) if q.result is not None else "-",
            }
            for i, q in enumerate(ir_gen.quadruples)
        ],
    }

    # 6. Timetable Generation (Execution Engine)
    generator = TimetableGenerator(analyzer, max_slots=max_slots)
    try:
        timetable = generator.generate()
        result["stages"]["generator"] = {
            "status": "passed",
            "assignments_count": len(timetable.assignments),
            "slots_used": len(timetable.slots_used()),
        }
    except TimetableGenerationError as e:
        result["stage_failed"] = "generator"
        result["error"] = {
            "category": "Timetable Generation Error",
            "message": str(e),
            "line": None,
            "column": None,
        }
        result["stages"]["generator"] = {"status": "failed", "error": str(e)}
        return result

    # 7. Independent Verifier
    violations = verify_timetable(timetable, analyzer=analyzer, max_slots=max_slots)
    if violations:
        result["stage_failed"] = "verifier"
        result["error"] = {
            "category": "Timetable Verification Error",
            "message": "\n".join(violations),
            "line": None,
            "column": None,
        }
        result["stages"]["verifier"] = {
            "status": "failed",
            "violations": violations,
        }
        return result

    result["stages"]["verifier"] = {
        "status": "passed",
        "violations": [],
    }

    # 8. Final Timetable Output
    assignments_data = [
        {
            "course": a.course,
            "room": a.room,
            "invigilator": a.invigilator,
            "students": a.student_group,
            "student_group": a.student_group,
            "slot": a.slot,
            "auto_assigned": a.auto_assigned,
        }
        for a in timetable.assignments
    ]
    result["stages"]["timetable"] = {
        "formatted": format_timetable(timetable),
        "by_slot": format_timetable_by_slot(timetable),
        "assignments": assignments_data,
        "slots_used": sorted(list(timetable.slots_used())),
    }

    result["success"] = True
    return result


class TimetableAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler supporting CORS and /api/compile."""

    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        if self.path in ("/", "/api", "/api/health"):
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "status": "ok",
                "service": "TimetableLang Compiler API",
                "version": "1.0.0"
            }).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/compile":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(post_data) if post_data else {}
            except json.JSONDecodeError:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Invalid JSON body"}).encode("utf-8"))
                return

            source = data.get("source", "")
            max_slots = data.get("max_slots")
            if max_slots is not None:
                try:
                    max_slots = int(max_slots)
                except ValueError:
                    max_slots = None

            result = compile_timetable_source(source, max_slots=max_slots)
            self._set_headers(200)
            self.wfile.write(json.dumps(result).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))


# Vercel WSGI / ASGI / HTTP handler compatibility
handler = TimetableAPIHandler


def run_local_server(port: int = 8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, TimetableAPIHandler)
    print(f"TimetableLang API server running on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_local_server(port)
