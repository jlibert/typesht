# compiler/parser.py
# AST Node definitions + Parser for TypeSht

from dataclasses import dataclass, field
from typing import Any, List, Optional
from .lexer import (
    Token,
    INT, FLOAT, STRING, FSTRING, BOOL, NONE,
    IDENT, DEF, CLASS, RETURN,
    IF, ELIF, ELSE, FOR, WHILE, IN, NOT_IN, RANGE,
    PRINT, SELF,
    AND, OR, NOT, LAMBDA, BREAK, CONTINUE, PASS,
    IMPORT, FROM, AS,
    T_STR, T_INT, T_FLOAT, T_BOOL, T_LIST, T_DICT,
    PLUS, MINUS, STAR, SLASH, DOUBLESLASH, PERCENT, POWER,
    EQ, NEQ, LT, GT, LTE, GTE,
    ASSIGN, PLUSEQ, MINUSEQ, STAREQ, SLASHEQ,
    LPAREN, RPAREN, LBRACKET, RBRACKET, LBRACE, RBRACE,
    COLON, COMMA, DOT, ARROW, AT,
    NEWLINE, INDENT, DEDENT, EOF,
)


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

@dataclass
class NumberNode:
    value: float | int

@dataclass
class StringNode:
    value: str

@dataclass
class BoolNode:
    value: bool

@dataclass
class NoneNode:
    pass

@dataclass
class IdentNode:
    name: str

@dataclass
class ImportNode:
    module:  str            # e.g. "math", "mymodule", "lodash"
    alias:   Optional[str]  # e.g. "m" from "import math as m"

@dataclass
class FromImportNode:
    module:  str            # e.g. "math", "mymodule"
    names:   List[Any]      # list of (name, alias) tuples

@dataclass
class LambdaNode:
    params: List[str]   # parameter names only, no type hints (matches Python spec)
    body:   Any         # single expression

@dataclass
class FStringNode:
    parts: List[Any]   # alternating StringNode (literal) and expr nodes

@dataclass
class BinOpNode:
    left:  Any
    op:    str
    right: Any

@dataclass
class UnaryOpNode:
    op:    str      # "not", "-"
    operand: Any

@dataclass
class AssignNode:
    name:     str
    value:    Any
    type_hint: Optional[str] = None   # "str", "int", "float", "bool", "list", "dict"

@dataclass
class AugAssignNode:
    name:  str
    op:    str      # "+", "-", "*", "/"
    value: Any

@dataclass
class ReturnNode:
    value: Any

@dataclass
class PrintNode:
    args:    List[Any]
    sep:     Optional[Any] = None
    end:     Optional[Any] = None

@dataclass
class IfNode:
    condition: Any
    body:      List[Any]
    elifs:     List[Any]        # list of (condition, body) tuples
    else_body: Optional[List[Any]] = None

@dataclass
class ForRangeNode:
    var:   str
    start: Any
    stop:  Any
    step:  Optional[Any]
    body:  List[Any]

@dataclass
class ForInNode:
    var:      str | List[str]   # list for tuple unpacking: for k, v in ...
    iterable: Any
    body:     List[Any]

@dataclass
class WhileNode:
    condition: Any
    body:      List[Any]

@dataclass
class BreakNode:
    pass

@dataclass
class ContinueNode:
    pass

@dataclass
class PassNode:
    pass

@dataclass
class FuncDefNode:
    name:        str
    params:      List[Any]      # list of (name, type_hint) tuples
    return_type: Optional[str]
    body:        List[Any]
    decorators:  List[str] = field(default_factory=list)  # e.g. ["staticmethod"]

@dataclass
class ClassDefNode:
    name:    str
    body:    List[Any]

@dataclass
class CallNode:
    func:  Any                  # IdentNode or AttrNode
    args:  List[Any]
    kwargs: List[Any] = field(default_factory=list)  # list of (name, value) tuples

@dataclass
class AttrNode:
    obj:  Any
    attr: str

@dataclass
class IndexNode:
    obj:   Any
    index: Any

@dataclass
class SliceNode:
    obj:   Any
    start: Optional[Any]
    stop:  Optional[Any]
    step:  Optional[Any] = None

@dataclass
class ListNode:
    elements: List[Any]

@dataclass
class DictNode:
    pairs: List[Any]            # list of (key, value) tuples

@dataclass
class MemberAssignNode:
    obj:   Any                  # the object being assigned to (e.g. self)
    attr:  str                  # attribute name
    value: Any


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParseError(Exception):
    def __init__(self, msg: str, token: Token):
        super().__init__(f"Line {token.line}: {msg} (got {token.type} {token.value!r})")
        self.token = token


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos    = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def peek(self, offset: int = 0) -> Token:
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != EOF:
            self.pos += 1
        return tok

    def check(self, *types) -> bool:
        return self.peek().type in types

    def match(self, *types) -> Optional[Token]:
        if self.check(*types):
            return self.advance()
        return None

    def expect(self, type: str, msg: str = "") -> Token:
        if self.check(type):
            return self.advance()
        raise ParseError(msg or f"Expected {type}", self.peek())

    def skip_newlines(self):
        while self.check(NEWLINE):
            self.advance()

    # ------------------------------------------------------------------
    # Type hint parsing
    # ------------------------------------------------------------------

    TYPE_TOKENS = {T_STR: "str", T_INT: "int", T_FLOAT: "float",
                   T_BOOL: "bool", T_LIST: "list", T_DICT: "dict"}

    def parse_type_hint(self) -> Optional[str]:
        tok = self.match(*self.TYPE_TOKENS)
        if tok:
            base = self.TYPE_TOKENS[tok.type]
            # handle generics: list[int], dict[str, int]
            if self.check(LBRACKET):
                self.advance()  # consume [
                params = [self.parse_type_hint()]
                while self.match(COMMA):
                    params.append(self.parse_type_hint())
                self.expect(RBRACKET)
                return f"{base}[{', '.join(p for p in params if p)}]"
            return base
        # handle unknown type names e.g. user-defined class names
        if self.check(IDENT) and self.peek(1).type in (ASSIGN, NEWLINE, RPAREN, COMMA, EOF):
            return self.advance().value
        return None

    # ------------------------------------------------------------------
    # Top-level parse
    # ------------------------------------------------------------------

    def parse(self) -> List[Any]:
        stmts = []
        self.skip_newlines()
        while not self.check(EOF):
            stmts.append(self.parse_statement())
            self.skip_newlines()
        return stmts

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def parse_statement(self) -> Any:
        tok = self.peek()

        # collect decorators before def
        if tok.type == AT:
            decorators = []
            while self.check(AT):
                self.advance()  # consume @
                name = self.expect(IDENT).value
                decorators.append(name)
                self.match(NEWLINE)
            node = self.parse_funcdef()
            node.decorators = decorators
            return node

        if tok.type == IMPORT:
            return self.parse_import()
        if tok.type == FROM:
            return self.parse_from_import()
        if tok.type == DEF:
            return self.parse_funcdef()
        if tok.type == CLASS:
            return self.parse_classdef()
        if tok.type == RETURN:
            return self.parse_return()
        if tok.type == IF:
            return self.parse_if()
        if tok.type == FOR:
            return self.parse_for()
        if tok.type == WHILE:
            return self.parse_while()
        if tok.type == PRINT:
            return self.parse_print()
        if tok.type == BREAK:
            self.advance()
            self.match(NEWLINE)
            return BreakNode()
        if tok.type == CONTINUE:
            self.advance()
            self.match(NEWLINE)
            return ContinueNode()
        if tok.type == PASS:
            self.advance()
            self.match(NEWLINE)
            return PassNode()

        return self.parse_assign_or_expr()

    def parse_block(self) -> List[Any]:
        """Parse an indented block of statements."""
        self.expect(INDENT)
        stmts = []
        self.skip_newlines()
        while not self.check(DEDENT) and not self.check(EOF):
            stmts.append(self.parse_statement())
            self.skip_newlines()
        self.expect(DEDENT)
        return stmts

    # ------------------------------------------------------------------
    # Assignment vs expression statement
    # ------------------------------------------------------------------

    def parse_assign_or_expr(self) -> Any:
        """
        Handles:
          name: type = expr       (typed assignment)
          name: type              (type-only declaration, e.g. class fields)
          name = expr             (untyped assignment)
          name += expr            (augmented assignment)
          self.attr = expr        (member assignment)
          expr                    (bare expression / call)
        """
        tok = self.peek()

        # self.attr = value
        if tok.type == SELF:
            return self.parse_member_assign_or_expr()

        # name : type = value  OR  name : type  OR  name = value  OR  name += value
        if tok.type == IDENT:
            next1 = self.peek(1)

            if next1.type == COLON:
                return self.parse_typed_assign()

            if next1.type == ASSIGN:
                name = self.advance().value
                self.advance()  # consume =
                value = self.parse_expr()
                self.match(NEWLINE)
                return AssignNode(name=name, value=value)

            if next1.type in (PLUSEQ, MINUSEQ, STAREQ, SLASHEQ):
                return self.parse_aug_assign()

        # fallthrough: bare expression (e.g. a function call on its own line)
        expr = self.parse_expr()
        self.match(NEWLINE)
        return expr

    def parse_typed_assign(self) -> AssignNode:
        name = self.advance().value         # IDENT
        self.expect(COLON)
        type_hint = self.parse_type_hint()
        # class field declarations have no value (e.g. "name: str")
        if not self.check(ASSIGN):
            self.match(NEWLINE)
            return AssignNode(name=name, value=None, type_hint=type_hint)
        self.expect(ASSIGN)
        value = self.parse_expr()
        self.match(NEWLINE)
        return AssignNode(name=name, value=value, type_hint=type_hint)

    def parse_aug_assign(self) -> AugAssignNode:
        name = self.advance().value
        op_tok = self.advance()
        op_map = {PLUSEQ: "+", MINUSEQ: "-", STAREQ: "*", SLASHEQ: "/"}
        op = op_map[op_tok.type]
        value = self.parse_expr()
        self.match(NEWLINE)
        return AugAssignNode(name=name, op=op, value=value)

    def parse_member_assign_or_expr(self) -> Any:
        """Parse self.attr = value or self.attr (bare read)."""
        expr = self.parse_expr()
        if self.match(ASSIGN):
            value = self.parse_expr()
            self.match(NEWLINE)
            if isinstance(expr, AttrNode):
                return MemberAssignNode(obj=expr.obj, attr=expr.attr, value=value)
            raise ParseError("Invalid assignment target", self.peek())
        self.match(NEWLINE)
        return expr

    # ------------------------------------------------------------------
    # Function & class definitions
    # ------------------------------------------------------------------

    def parse_funcdef(self) -> FuncDefNode:
        self.expect(DEF)
        name = self.expect(IDENT).value
        self.expect(LPAREN)
        params = self.parse_params()
        self.expect(RPAREN)
        return_type = None
        if self.match(ARROW):
            return_type = self.parse_type_hint()
        self.expect(COLON)
        self.match(NEWLINE)
        body = self.parse_block()
        return FuncDefNode(name=name, params=params,
                           return_type=return_type, body=body)

    def parse_params(self) -> List[Any]:
        params = []
        if self.check(RPAREN):
            return params
        while True:
            if self.check(SELF):
                self.advance()
                params.append(("self", None))
            else:
                pname = self.expect(IDENT).value
                ptype = None
                if self.match(COLON):
                    ptype = self.parse_type_hint()
                params.append((pname, ptype))
            if not self.match(COMMA):
                break
        return params

    def parse_classdef(self) -> ClassDefNode:
        self.expect(CLASS)
        name = self.expect(IDENT).value
        self.expect(COLON)
        self.match(NEWLINE)
        body = self.parse_block()
        return ClassDefNode(name=name, body=body)

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def parse_return(self) -> ReturnNode:
        self.expect(RETURN)
        value = None
        if not self.check(NEWLINE) and not self.check(EOF):
            value = self.parse_expr()
        self.match(NEWLINE)
        return ReturnNode(value=value)

    def parse_if(self) -> IfNode:
        self.expect(IF)
        condition = self.parse_expr()
        self.expect(COLON)
        self.match(NEWLINE)
        body = self.parse_block()

        elifs = []
        while self.check(ELIF):
            self.advance()
            elif_cond = self.parse_expr()
            self.expect(COLON)
            self.match(NEWLINE)
            elif_body = self.parse_block()
            elifs.append((elif_cond, elif_body))

        else_body = None
        if self.match(ELSE):
            self.expect(COLON)
            self.match(NEWLINE)
            else_body = self.parse_block()

        return IfNode(condition=condition, body=body,
                      elifs=elifs, else_body=else_body)

    def parse_for(self) -> Any:
        self.expect(FOR)

        # collect loop variable(s) — handles "for k, v in ..."
        vars_ = [self.expect(IDENT).value]
        while self.match(COMMA):
            vars_.append(self.expect(IDENT).value)
        var = vars_[0] if len(vars_) == 1 else vars_

        self.expect(IN)

        # for i in range(...)
        if self.check(RANGE):
            return self.parse_for_range(var)

        iterable = self.parse_expr()
        self.expect(COLON)
        self.match(NEWLINE)
        body = self.parse_block()
        return ForInNode(var=var, iterable=iterable, body=body)

    def parse_for_range(self, var: str) -> ForRangeNode:
        self.expect(RANGE)
        self.expect(LPAREN)
        args = [self.parse_expr()]
        while self.match(COMMA):
            args.append(self.parse_expr())
        self.expect(RPAREN)
        self.expect(COLON)
        self.match(NEWLINE)
        body = self.parse_block()

        if len(args) == 1:
            start, stop, step = NumberNode(0), args[0], None
        elif len(args) == 2:
            start, stop, step = args[0], args[1], None
        else:
            start, stop, step = args[0], args[1], args[2]

        return ForRangeNode(var=var, start=start, stop=stop, step=step, body=body)

    def parse_while(self) -> WhileNode:
        self.expect(WHILE)
        condition = self.parse_expr()
        self.expect(COLON)
        self.match(NEWLINE)
        body = self.parse_block()
        return WhileNode(condition=condition, body=body)

    def parse_print(self) -> PrintNode:
        self.expect(PRINT)
        self.expect(LPAREN)
        args, sep, end = [], None, None
        while not self.check(RPAREN):
            # keyword args: sep= or end=
            if self.check(IDENT) and self.peek().value in ("sep", "end") \
                    and self.peek(1).type == ASSIGN:
                kw = self.advance().value
                self.advance()  # =
                val = self.parse_expr()
                if kw == "sep":
                    sep = val
                else:
                    end = val
            else:
                args.append(self.parse_expr())
            if not self.match(COMMA):
                break
        self.expect(RPAREN)
        self.match(NEWLINE)
        return PrintNode(args=args, sep=sep, end=end)

    # ------------------------------------------------------------------
    # Expressions  (precedence climbing)
    # ------------------------------------------------------------------

    def parse_expr(self) -> Any:
        return self.parse_or()

    def parse_or(self) -> Any:
        left = self.parse_and()
        while self.check(OR):
            self.advance()
            left = BinOpNode(left, "or", self.parse_and())
        return left

    def parse_and(self) -> Any:
        left = self.parse_not()
        while self.check(AND):
            self.advance()
            left = BinOpNode(left, "and", self.parse_not())
        return left

    def parse_not(self) -> Any:
        if self.match(NOT):
            return UnaryOpNode("not", self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self) -> Any:
        left = self.parse_add()
        CMP = {EQ: "==", NEQ: "!=", LT: "<", GT: ">", LTE: "<=", GTE: ">=",
               IN: "in", NOT_IN: "not in"}
        while self.peek().type in CMP:
            op = CMP[self.advance().type]
            left = BinOpNode(left, op, self.parse_add())
        return left

    def parse_add(self) -> Any:
        left = self.parse_mul()
        while self.peek().type in (PLUS, MINUS):
            op = "+" if self.advance().type == PLUS else "-"
            left = BinOpNode(left, op, self.parse_mul())
        return left

    def parse_mul(self) -> Any:
        left = self.parse_unary()
        OPS = {STAR: "*", SLASH: "/", DOUBLESLASH: "//", PERCENT: "%"}
        while self.peek().type in OPS:
            op = OPS[self.advance().type]
            left = BinOpNode(left, op, self.parse_unary())
        return left

    def parse_unary(self) -> Any:
        if self.match(MINUS):
            return UnaryOpNode("-", self.parse_power())
        return self.parse_power()

    def parse_power(self) -> Any:
        base = self.parse_postfix()
        if self.match(POWER):
            return BinOpNode(base, "**", self.parse_unary())
        return base

    def parse_postfix(self) -> Any:
        """Handle attribute access, subscript, and calls after a primary."""
        node = self.parse_primary()
        while True:
            if self.match(DOT):
                attr = self.expect(IDENT).value
                node = AttrNode(obj=node, attr=attr)
                # method call
                if self.check(LPAREN):
                    node = self.finish_call(node)
            elif self.check(LBRACKET):
                node = self.parse_subscript(node)
            elif self.check(LPAREN):
                node = self.finish_call(node)
            else:
                break
        return node

    def parse_subscript(self, obj: Any) -> Any:
        """Parse obj[index] or obj[start:stop] or obj[start:stop:step]."""
        self.expect(LBRACKET)
        start = None if self.check(COLON) else self.parse_expr()

        if self.match(COLON):
            stop = None
            if not self.check(RBRACKET) and not self.check(COLON):
                stop = self.parse_expr()
            step = None
            if self.match(COLON):
                if not self.check(RBRACKET):
                    step = self.parse_expr()
            self.expect(RBRACKET)
            return SliceNode(obj=obj, start=start, stop=stop, step=step)

        self.expect(RBRACKET)
        return IndexNode(obj=obj, index=start)

    def finish_call(self, func: Any) -> CallNode:
        """Parse argument list for a call that's already identified its callee."""
        self.expect(LPAREN)
        args, kwargs = [], []
        while not self.check(RPAREN):
            if self.check(IDENT) and self.peek(1).type == ASSIGN:
                kw = self.advance().value
                self.advance()  # =
                kwargs.append((kw, self.parse_expr()))
            else:
                args.append(self.parse_expr())
            if not self.match(COMMA):
                break
        self.expect(RPAREN)
        return CallNode(func=func, args=args, kwargs=kwargs)

    # ------------------------------------------------------------------
    # Primary expressions
    # ------------------------------------------------------------------

    def parse_primary(self) -> Any:
        tok = self.peek()

        if tok.type == INT:
            self.advance()
            return NumberNode(tok.value)

        if tok.type == FLOAT:
            self.advance()
            return NumberNode(tok.value)

        if tok.type == STRING:
            self.advance()
            return StringNode(tok.value)

        if tok.type == BOOL:
            self.advance()
            return BoolNode(tok.value)

        if tok.type == NONE:
            self.advance()
            return NoneNode()

        if tok.type == SELF:
            self.advance()
            return IdentNode("self")

        if tok.type == IDENT:
            self.advance()
            return IdentNode(tok.value)

        if tok.type == LAMBDA:
            return self.parse_lambda()

        if tok.type == FSTRING:
            self.advance()
            return self.parse_fstring(tok.value)

        if tok.type == LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(RPAREN)
            return expr

        if tok.type == LBRACKET:
            return self.parse_list()

        if tok.type == LBRACE:
            return self.parse_dict()

        raise ParseError(f"Unexpected token", tok)

    def parse_import(self) -> ImportNode:
        """Parse: import module [as alias]"""
        self.expect(IMPORT)
        # module name may be dotted e.g. "os.path"
        parts = [self.expect(IDENT).value]
        while self.match(DOT):
            parts.append(self.expect(IDENT).value)
        module = ".".join(parts)
        alias = None
        if self.match(AS):
            alias = self.expect(IDENT).value
        self.match(NEWLINE)
        return ImportNode(module=module, alias=alias)

    def parse_from_import(self) -> FromImportNode:
        """Parse: from module import name1 [as alias1], name2 [as alias2], ..."""
        self.expect(FROM)
        # module name may be dotted
        parts = [self.expect(IDENT).value]
        while self.match(DOT):
            parts.append(self.expect(IDENT).value)
        module = ".".join(parts)
        self.expect(IMPORT)
        names = []
        # handle "from module import *"
        if self.match(STAR):
            names.append(("*", None))
        else:
            while True:
                name = self.expect(IDENT).value
                alias = None
                if self.match(AS):
                    alias = self.expect(IDENT).value
                names.append((name, alias))
                if not self.match(COMMA):
                    break
        self.match(NEWLINE)
        return FromImportNode(module=module, names=names)

    def parse_lambda(self) -> LambdaNode:
        """Parse: lambda param1, param2, ...: expr"""
        self.expect(LAMBDA)
        params = []
        # collect parameter names until we hit the colon
        while not self.check(COLON):
            params.append(self.expect(IDENT).value)
            if not self.match(COMMA):
                break
        self.expect(COLON)
        body = self.parse_expr()
        return LambdaNode(params=params, body=body)

    def parse_fstring(self, raw: str) -> FStringNode:
        """Split raw f-string content into literal and expression parts,
        then parse each expression using a nested Parser."""
        parts = []
        i = 0
        current_lit = []

        while i < len(raw):
            ch = raw[i]

            if ch == "{":
                # flush any accumulated literal
                if current_lit:
                    parts.append(StringNode("".join(current_lit)))
                    current_lit = []

                # find matching closing brace (respecting depth + nested quotes)
                depth = 1
                j = i + 1
                inner_quote = None
                while j < len(raw) and depth > 0:
                    c = raw[j]
                    if inner_quote:
                        if c == "\\" and j + 1 < len(raw):
                            j += 2
                            continue
                        if c == inner_quote:
                            inner_quote = None
                    else:
                        if c in ('"', "'"):
                            inner_quote = c
                        elif c == "{":
                            depth += 1
                        elif c == "}":
                            depth -= 1
                    j += 1

                expr_src = raw[i+1:j-1]

                # parse the expression using the full lexer + parser pipeline
                from .lexer import lex as _lex
                expr_tokens = _lex(expr_src)
                expr_node   = Parser(expr_tokens).parse_expr()
                parts.append(expr_node)
                i = j

            elif ch == "\\" and i + 1 < len(raw):
                esc = raw[i+1]
                current_lit.append({"n": "\n", "t": "\t", "\\": "\\"}.get(esc, esc))
                i += 2

            else:
                current_lit.append(ch)
                i += 1

        # flush remaining literal
        if current_lit:
            parts.append(StringNode("".join(current_lit)))

        return FStringNode(parts=parts)

    def parse_list(self) -> ListNode:
        self.expect(LBRACKET)
        elements = []
        while not self.check(RBRACKET):
            elements.append(self.parse_expr())
            if not self.match(COMMA):
                break
        self.expect(RBRACKET)
        return ListNode(elements=elements)

    def parse_dict(self) -> DictNode:
        self.expect(LBRACE)
        pairs = []
        while not self.check(RBRACE):
            key = self.parse_expr()
            self.expect(COLON)
            val = self.parse_expr()
            pairs.append((key, val))
            if not self.match(COMMA):
                break
        self.expect(RBRACE)
        return DictNode(pairs=pairs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(tokens) -> List[Any]:
    """Parse a token list into an AST. Returns a list of top-level nodes."""
    return Parser(tokens).parse()