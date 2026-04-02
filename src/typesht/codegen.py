# compiler/codegen.py
# TypeScript code generator for TypeSht

from typing import Optional
from .parser import (
    NumberNode, StringNode, BoolNode, NoneNode, FStringNode, LambdaNode,
    IdentNode, BinOpNode, UnaryOpNode,
    AssignNode, AugAssignNode, MemberAssignNode,
    ReturnNode, PrintNode,
    IfNode, ForRangeNode, ForInNode, WhileNode,
    BreakNode, ContinueNode, PassNode,
    FuncDefNode, ClassDefNode,
    CallNode, AttrNode, IndexNode, SliceNode,
    ListNode, DictNode,
    ImportNode, FromImportNode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_camel(name: str) -> str:
    """Convert snake_case to camelCase. Leaves already-camel names untouched."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])

TYPE_MAP = {
    "str":   "string",
    "int":   "number",
    "float": "number",
    "bool":  "boolean",
    "list":  "any[]",
    "dict":  "any",
}

# Maps TypeSht primitive type names to TypeScript equivalents for use
# inside generic parameters e.g. list[int] → number[]
GENERIC_TYPE_MAP = {
    "str":   "string",
    "int":   "number",
    "float": "number",
    "bool":  "boolean",
}

def resolve_type(hint) -> Optional[str]:
    """Resolve a type hint string (possibly generic) to a TypeScript type string.
    Returns None if the hint is unknown or should be omitted."""
    if hint is None:
        return None
    # plain known type
    if hint in TYPE_MAP:
        return TYPE_MAP[hint]
    # generic: list[x] or dict[k, v]
    if hint.startswith("list[") and hint.endswith("]"):
        inner = hint[5:-1].strip()
        ts_inner = GENERIC_TYPE_MAP.get(inner, "any")
        return f"{ts_inner}[]"
    if hint.startswith("dict[") and hint.endswith("]"):
        return "any"  # PyDict is runtime type regardless of params
    return None  # unknown type — omit annotation

# Python stdlib modules that are provided by typesht-runtime
STDLIB_MODULES = {"math", "random", "json", "re", "sys", "os"}

# Built-in decorators that map to TypeScript keywords — not higher-order calls
BUILTIN_DECORATORS = {"staticmethod", "classmethod", "property"}


# ---------------------------------------------------------------------------
# CodeGen
# ---------------------------------------------------------------------------

class CodeGen:
    def __init__(self):
        self.indent  = 0
        self.lines   = []
        self.classes = set()   # tracks class names so calls get "new" prefix

    def pad(self) -> str:
        return "    " * self.indent

    def emit(self, line: str):
        self.lines.append(self.pad() + line)

    def generate(self, ast: list) -> str:
        self._collect_classes(ast)
        self.emit('import * as $ from "typesht-runtime";')
        self.emit("")
        for node in ast:
            self.gen_stmt(node)
        return "\n".join(self.lines)

    def _collect_classes(self, ast: list):
        """First pass — collect all class names before emitting code.
        This ensures forward references to classes get the 'new' prefix."""
        for node in ast:
            if isinstance(node, ClassDefNode):
                self.classes.add(node.name)

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def gen(self, node) -> str:
        """Dispatch to gen_* method. Returns a string for expression nodes;
        emits lines directly for statement nodes."""
        method = f"gen_{type(node).__name__}"
        fn = getattr(self, method, None)
        if fn is None:
            raise NotImplementedError(f"No codegen for {type(node).__name__}")
        return fn(node)

    def gen_stmt(self, node):
        """Use this when a node appears as a statement (top level or in a body).
        Handles expression nodes like CallNode that return a string instead of
        emitting directly — wraps them in an emit so they appear in output."""
        result = self.gen(node)
        if isinstance(result, str):
            self.emit(f"{result};")

    # ------------------------------------------------------------------
    # Literals
    # ------------------------------------------------------------------

    def gen_NumberNode(self, node) -> str:
        return str(node.value)

    def gen_StringNode(self, node) -> str:
        escaped = node.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
        return f'"{escaped}"'

    def gen_BoolNode(self, node) -> str:
        return "true" if node.value else "false"

    def gen_NoneNode(self, node) -> str:
        return "null"

    # ------------------------------------------------------------------
    # Identifiers & access
    # ------------------------------------------------------------------

    def gen_IdentNode(self, node) -> str:
        if node.name == "self":
            return "this"
        return to_camel(node.name)

    def gen_AttrNode(self, node) -> str:
        obj  = self.gen(node.obj)
        attr = to_camel(node.attr)
        return f"{obj}.{attr}"

    def gen_IndexNode(self, node) -> str:
        obj   = self.gen(node.obj)
        index = self.gen(node.index)
        return f"$.index({obj}, {index})"

    def gen_SliceNode(self, node) -> str:
        obj   = self.gen(node.obj)
        start = self.gen(node.start) if node.start is not None else "null"
        stop  = self.gen(node.stop)  if node.stop  is not None else "null"
        step  = self.gen(node.step)  if node.step  is not None else "null"
        return f"$.slice({obj}, {start}, {stop}, {step})"

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def gen_ListNode(self, node) -> str:
        elements = ", ".join(self.gen(e) for e in node.elements)
        return f"[{elements}]"

    def gen_DictNode(self, node) -> str:
        pairs = ", ".join(
            f"[{self.gen(k)}, {self.gen(v)}]" for k, v in node.pairs
        )
        return f"$.dict([{pairs}])"

    # ------------------------------------------------------------------
    # Operators
    # ------------------------------------------------------------------

    def gen_BinOpNode(self, node) -> str:
        left  = self.gen(node.left)
        right = self.gen(node.right)
        op    = node.op

        if op == "//":
            return f"$.floordiv({left}, {right})"
        if op == "%":
            return f"$.pymod({left}, {right})"
        if op == "**":
            return f"Math.pow({left}, {right})"
        if op == "==":
            return f"{left} === {right}"
        if op == "!=":
            return f"{left} !== {right}"
        if op == "in":
            return f"$.contains({right}, {left})"
        if op == "not in":
            return f"!$.contains({right}, {left})"
        if op == "and":
            return f"{left} && {right}"
        if op == "or":
            return f"{left} || {right}"

        return f"{left} {op} {right}"

    def gen_UnaryOpNode(self, node) -> str:
        operand = self.gen(node.operand)
        if node.op == "not":
            return f"!{operand}"
        if node.op == "-":
            return f"-{operand}"
        raise NotImplementedError(f"Unknown unary op: {node.op}")

    # ------------------------------------------------------------------
    # F-strings
    # ------------------------------------------------------------------

    def gen_FStringNode(self, node) -> str:
        parts = []
        for part in node.parts:
            if isinstance(part, StringNode):
                text = part.value.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
                parts.append(text)
            else:
                parts.append(f"${{{self.gen(part)}}}")
        return f"`{''.join(parts)}`"

    # ------------------------------------------------------------------
    # Lambdas
    # ------------------------------------------------------------------

    def gen_LambdaNode(self, node) -> str:
        params = ", ".join(f"{to_camel(p)}: any" for p in node.params)
        body   = self.gen(node.body)
        return f"({params}) => {body}"

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def gen_AssignNode(self, node):
        name    = to_camel(node.name)
        ts_type = resolve_type(node.type_hint)
        # type-only declaration (e.g. class field "name: str" with no value)
        if node.value is None:
            self.emit(f"let {name}: {ts_type or 'any'};")
            return
        value = self.gen(node.value)
        if ts_type:
            self.emit(f"let {name}: {ts_type} = {value};")
        else:
            self.emit(f"let {name} = {value};")

    def gen_AugAssignNode(self, node):
        name  = to_camel(node.name)
        value = self.gen(node.value)
        self.emit(f"{name} {node.op}= {value};")

    def gen_MemberAssignNode(self, node):
        obj   = self.gen(node.obj)
        attr  = to_camel(node.attr)
        value = self.gen(node.value)
        self.emit(f"{obj}.{attr} = {value};")

    # ------------------------------------------------------------------
    # Return & print
    # ------------------------------------------------------------------

    def gen_ReturnNode(self, node):
        if node.value is None:
            self.emit("return;")
        else:
            self.emit(f"return {self.gen(node.value)};")

    def gen_PrintNode(self, node):
        args = [self.gen(a) for a in node.args]
        if node.sep is not None:
            args.append(f"{{sep: {self.gen(node.sep)}}}")
        if node.end is not None:
            args.append(f"{{end: {self.gen(node.end)}}}")
        self.emit(f"$.print({', '.join(args)});")

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def gen_IfNode(self, node):
        self.emit(f"if ({self.gen(node.condition)}) {{")
        self.indent += 1
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.indent -= 1

        for elif_cond, elif_body in node.elifs:
            self.emit(f"}} else if ({self.gen(elif_cond)}) {{")
            self.indent += 1
            for stmt in elif_body:
                self.gen_stmt(stmt)
            self.indent -= 1

        if node.else_body is not None:
            self.emit("} else {")
            self.indent += 1
            for stmt in node.else_body:
                self.gen_stmt(stmt)
            self.indent -= 1

        self.emit("}")

    def gen_ForRangeNode(self, node):
        var   = to_camel(node.var)
        start = self.gen(node.start)
        stop  = self.gen(node.stop)
        step  = self.gen(node.step) if node.step is not None else "1"
        self.emit(f"for (let {var} = {start}; {var} < {stop}; {var} += {step}) {{")
        self.indent += 1
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.indent -= 1
        self.emit("}")

    def gen_ForInNode(self, node):
        iterable = self.gen(node.iterable)
        if isinstance(node.var, list):
            var = f"[{', '.join(to_camel(v) for v in node.var)}]"
        else:
            var = to_camel(node.var)
        self.emit(f"for (const {var} of {iterable}) {{")
        self.indent += 1
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.indent -= 1
        self.emit("}")

    def gen_WhileNode(self, node):
        self.emit(f"while ({self.gen(node.condition)}) {{")
        self.indent += 1
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.indent -= 1
        self.emit("}")

    def gen_BreakNode(self, node):
        self.emit("break;")

    def gen_ContinueNode(self, node):
        self.emit("continue;")

    def gen_PassNode(self, node):
        pass

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def gen_ImportNode(self, node):
        module = node.module
        alias  = to_camel(node.alias) if node.alias else None

        if module in STDLIB_MODULES:
            if alias and alias != module:
                self.emit(f'import {{ {module} as {alias} }} from "typesht-runtime";')
            else:
                self.emit(f'import {{ {module} }} from "typesht-runtime";')
        else:
            out_name = alias if alias else to_camel(module)
            self.emit(f'import * as {out_name} from "./{module}.js";')

    def gen_FromImportNode(self, node):
        module = node.module
        names  = node.names

        if module in STDLIB_MODULES:
            # from math import sqrt → import { math } from "typesht-runtime"
            # then emit const aliases
            self.emit(f'import {{ {module} }} from "typesht-runtime";')
            for name, alias in names:
                if name == "*":
                    # from math import * — not ideal but handle gracefully
                    self.emit(f"const {{ ...{module}Exports }} = {module};")
                else:
                    out_name = to_camel(alias if alias else name)
                    self.emit(f"const {out_name} = {module}.{to_camel(name)};")
        else:
            # user module or npm package
            if len(names) == 1 and names[0][0] == "*":
                self.emit(f'import * as {to_camel(module)} from "./{module}.js";')
            else:
                parts = []
                for name, alias in names:
                    if alias:
                        parts.append(f"{to_camel(name)} as {to_camel(alias)}")
                    else:
                        parts.append(to_camel(name))
                self.emit(f'import {{ {", ".join(parts)} }} from "./{module}.js";')

    # ------------------------------------------------------------------
    # Functions & classes
    # ------------------------------------------------------------------

    def gen_FuncDefNode(self, node):
        is_init = node.name == "__init__"
        name    = to_camel(node.name)
        ret     = resolve_type(node.return_type) or "any"

        params = []
        for pname, ptype in node.params:
            if pname == "self":
                continue
            ts_type = resolve_type(ptype) or "any"
            params.append(f"{to_camel(pname)}: {ts_type}")

        if is_init:
            self.emit(f"constructor({', '.join(params)}) {{")
        else:
            self.emit(f"function {name}({', '.join(params)}): {ret} {{")

        self.indent += 1
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.indent -= 1
        self.emit("}")

        # emit higher-order function calls for custom decorators
        # apply in reverse order to match Python's decorator application order
        custom = [d for d in reversed(node.decorators)
                  if d not in BUILTIN_DECORATORS]
        for decorator in custom:
            self.emit(f"{name} = {to_camel(decorator)}({name});")

    def gen_ClassDefNode(self, node):
        self.emit(f"class {node.name} {{")
        self.indent += 1

        for item in node.body:
            if isinstance(item, AssignNode):
                ts_type = resolve_type(item.type_hint) or "any"
                self.emit(f"{to_camel(item.name)}: {ts_type};")

        for item in node.body:
            if isinstance(item, FuncDefNode):
                self._gen_method(item)

        self.indent -= 1
        self.emit("}")

    def _gen_method(self, node: FuncDefNode):
        """Emit a class method (no leading 'function' keyword)."""
        is_init     = node.name == "__init__"
        is_static   = "staticmethod" in node.decorators or "classmethod" in node.decorators
        is_property = "property" in node.decorators
        name        = to_camel(node.name)
        ret         = resolve_type(node.return_type) or "any"

        params = []
        for pname, ptype in node.params:
            if pname in ("self", "cls"):
                continue
            ts_type = resolve_type(ptype) or "any"
            params.append(f"{to_camel(pname)}: {ts_type}")

        prefix = "static " if is_static else ""

        if is_init:
            self.emit(f"constructor({', '.join(params)}) {{")
        elif is_property:
            self.emit(f"get {name}(): {ret} {{")
        else:
            self.emit(f"{prefix}{name}({', '.join(params)}): {ret} {{")

        self.indent += 1
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.indent -= 1
        self.emit("}")

        # emit higher-order wrapping for custom decorators on class methods
        custom = [d for d in reversed(node.decorators)
                  if d not in BUILTIN_DECORATORS]
        for decorator in custom:
            self.emit(f"this.{name} = {to_camel(decorator)}(this.{name});")

    # ------------------------------------------------------------------
    # Calls
    # ------------------------------------------------------------------

    def gen_CallNode(self, node) -> str:
        func = self.gen(node.func)
        args = [self.gen(a) for a in node.args]
        for kw, val in node.kwargs:
            args.append(f"{kw}: {self.gen(val)}")
        # prefix with "new" if calling a known class constructor
        if isinstance(node.func, IdentNode) and node.func.name in self.classes:
            return f"new {func}({', '.join(args)})"
        return f"{func}({', '.join(args)})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(ast: list) -> str:
    """Walk an AST and return a TypeScript source string."""
    return CodeGen().generate(ast)