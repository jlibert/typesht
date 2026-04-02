# compiler/lexer.py
# Tokenizer / Lexer for TypeSht

from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

TT = str  # token type alias for readability

# Literals
INT       = "INT"
FLOAT     = "FLOAT"
STRING    = "STRING"
FSTRING   = "FSTRING"   # f"..." — raw content preserved for parser
BOOL      = "BOOL"        # True / False

# Identifiers & keywords
IDENT     = "IDENT"
DEF       = "DEF"
CLASS     = "CLASS"
RETURN    = "RETURN"
IF        = "IF"
ELIF      = "ELIF"
ELSE      = "ELSE"
FOR       = "FOR"
WHILE     = "WHILE"
IN        = "IN"
NOT_IN    = "NOT_IN"      # "not in"
RANGE     = "RANGE"
PRINT     = "PRINT"
SELF      = "SELF"
NONE      = "NONE"        # None literal
AND       = "AND"
OR        = "OR"
NOT       = "NOT"
LAMBDA    = "LAMBDA"
BREAK     = "BREAK"
CONTINUE  = "CONTINUE"
PASS      = "PASS"
IMPORT    = "IMPORT"
FROM      = "FROM"
AS        = "AS"

# Type names (treated as keywords so the parser can identify them easily)
T_STR     = "T_STR"
T_INT     = "T_INT"
T_FLOAT   = "T_FLOAT"
T_BOOL    = "T_BOOL"
T_LIST    = "T_LIST"
T_DICT    = "T_DICT"

# Operators
PLUS      = "PLUS"        # +
MINUS     = "MINUS"       # -
STAR      = "STAR"        # *
SLASH     = "SLASH"       # /
DOUBLESLASH = "DOUBLESLASH"  # //
PERCENT   = "PERCENT"     # %
POWER     = "POWER"       # **
EQ        = "EQ"          # ==
NEQ       = "NEQ"         # !=
LT        = "LT"          # <
GT        = "GT"          # >
LTE       = "LTE"         # <=
GTE       = "GTE"         # >=
ASSIGN    = "ASSIGN"      # =
PLUSEQ    = "PLUSEQ"      # +=
MINUSEQ   = "MINUSEQ"     # -=
STAREQ    = "STAREQ"      # *=
SLASHEQ   = "SLASHEQ"     # /=

# Delimiters
LPAREN    = "LPAREN"      # (
RPAREN    = "RPAREN"      # )
LBRACKET  = "LBRACKET"    # [
RBRACKET  = "RBRACKET"    # ]
LBRACE    = "LBRACE"      # {
RBRACE    = "RBRACE"      # }
COLON     = "COLON"       # :
COMMA     = "COMMA"       # ,
DOT       = "DOT"         # .
AT        = "AT"          # @
ARROW     = "ARROW"       # ->
NEWLINE   = "NEWLINE"     # \n
INDENT    = "INDENT"      # increased indentation
DEDENT    = "DEDENT"      # decreased indentation
EOF       = "EOF"


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: TT
    value: object          # str, int, float, bool, or None
    line: int = 0

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


# ---------------------------------------------------------------------------
# Keywords table
# ---------------------------------------------------------------------------

KEYWORDS: dict[str, TT] = {
    "def":      DEF,
    "class":    CLASS,
    "return":   RETURN,
    "if":       IF,
    "elif":     ELIF,
    "else":     ELSE,
    "for":      FOR,
    "while":    WHILE,
    "in":       IN,
    "range":    RANGE,
    "print":    PRINT,
    "self":     SELF,
    "True":     BOOL,
    "False":    BOOL,
    "None":     NONE,
    "and":      AND,
    "or":       OR,
    "not":      NOT,
    "lambda":   LAMBDA,
    "break":    BREAK,
    "continue": CONTINUE,
    "pass":     PASS,
    "import":   IMPORT,
    "from":     FROM,
    "as":       AS,
    # type names
    "str":      T_STR,
    "int":      T_INT,
    "float":    T_FLOAT,
    "bool":     T_BOOL,
    "list":     T_LIST,
    "dict":     T_DICT,
}


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class LexError(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(f"Line {line}: {msg}")
        self.line = line


class Lexer:
    def __init__(self, source: str):
        self.src    = source
        self.pos    = 0
        self.line   = 1
        self.tokens: List[Token] = []

        # Indentation stack — always starts with 0 (no indent)
        self.indent_stack: List[int] = [0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def peek(self, offset: int = 0) -> str:
        """Return character at pos+offset without advancing, or '' at EOF."""
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def advance(self) -> str:
        """Consume and return the current character."""
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def match(self, expected: str) -> bool:
        """Consume the next character only if it matches expected."""
        if self.peek() == expected:
            self.advance()
            return True
        return False

    def add(self, type: TT, value: object = None):
        self.tokens.append(Token(type, value, self.line))

    # ------------------------------------------------------------------
    # Indentation handling
    # ------------------------------------------------------------------

    def handle_indent(self, level: int):
        """Emit INDENT / DEDENT tokens based on new indentation level."""
        current = self.indent_stack[-1]

        if level > current:
            self.indent_stack.append(level)
            self.add(INDENT, level)

        elif level < current:
            while self.indent_stack[-1] > level:
                self.indent_stack.pop()
                self.add(DEDENT, level)
            if self.indent_stack[-1] != level:
                raise LexError(
                    f"Indentation level {level} does not match any outer block",
                    self.line
                )

        # level == current → no token needed

    # ------------------------------------------------------------------
    # Sub-scanners
    # ------------------------------------------------------------------

    def scan_triple_string(self, quote: str) -> str:
        """Scan a triple-quoted string, preserving all whitespace and newlines."""
        result = []
        closing = quote * 3
        while self.pos < len(self.src):
            if self.src[self.pos:self.pos + 3] == closing:
                self.pos += 3
                return "".join(result)
            ch = self.advance()
            if ch == "\\":
                esc = self.advance()
                result.append({"n": "\n", "t": "\t", "\\": "\\"}.get(esc, esc))
            else:
                result.append(ch)
        raise LexError("Unterminated triple-quoted string", self.line)

    def scan_fstring(self, quote: str) -> str:
        """Scan an f-string, preserving {expr} blocks and handling:
        - nested quotes inside expressions
        - brace depth tracking
        - escape sequences in literal parts
        Returns the raw content between the outer quotes.
        """
        result = []
        while self.pos < len(self.src):
            ch = self.advance()

            if ch == quote:
                return "".join(result)

            if ch == "\\":
                esc = self.advance()
                result.append("\\" + esc)
                continue

            if ch == "{":
                if self.peek() == "{":
                    self.advance()
                    result.append("{")
                    continue
                result.append("{")
                depth = 1
                inner_quote = None
                while self.pos < len(self.src) and depth > 0:
                    c = self.advance()
                    if inner_quote:
                        if c == "\\":
                            result.append(c)
                            result.append(self.advance())
                        elif c == inner_quote:
                            result.append(c)
                            inner_quote = None
                        else:
                            result.append(c)
                    else:
                        if c in ('"', "'"):
                            inner_quote = c
                            result.append(c)
                        elif c == "{":
                            depth += 1
                            result.append(c)
                        elif c == "}":
                            depth -= 1
                            result.append(c)
                        else:
                            result.append(c)
                continue

            if ch == "}":
                if self.peek() == "}":
                    self.advance()
                    result.append("}")
                    continue
                raise LexError("Single '}' in f-string", self.line)

            result.append(ch)

        raise LexError("Unterminated f-string", self.line)

    def scan_string(self, quote: str) -> str:
        """Scan a single- or double-quoted string, handling escape sequences."""
        result = []
        while self.pos < len(self.src):
            ch = self.advance()
            if ch == quote:
                return "".join(result)
            if ch == "\\":
                esc = self.advance()
                result.append({"n": "\n", "t": "\t", "\\": "\\"}.get(esc, esc))
            else:
                result.append(ch)
        raise LexError("Unterminated string literal", self.line)

    def scan_number(self, first: str) -> Token:
        """Scan an integer or float literal."""
        digits = [first]
        while self.peek().isdigit():
            digits.append(self.advance())

        if self.peek() == "." and self.peek(1).isdigit():
            digits.append(self.advance())
            while self.peek().isdigit():
                digits.append(self.advance())
            return Token(FLOAT, float("".join(digits)), self.line)

        return Token(INT, int("".join(digits)), self.line)

    def scan_ident_or_keyword(self, first: str) -> Token:
        """Scan an identifier or keyword (including 'not in')."""
        chars = [first]
        while self.peek().isalnum() or self.peek() == "_":
            chars.append(self.advance())
        word = "".join(chars)

        # Special two-word token: "not in"
        if word == "not":
            tmp = self.pos
            while tmp < len(self.src) and self.src[tmp] in (" ", "\t"):
                tmp += 1
            if self.src[tmp:tmp+2] == "in" and not (
                tmp + 2 < len(self.src) and (self.src[tmp+2].isalnum() or self.src[tmp+2] == "_")
            ):
                self.pos = tmp + 2
                return Token(NOT_IN, "not in", self.line)

        tt    = KEYWORDS.get(word, IDENT)
        value = {"True": True, "False": False}.get(word, word)
        return Token(tt, value, self.line)

    # ------------------------------------------------------------------
    # Main tokenize loop — character-by-character over entire source
    # ------------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        self.pos  = 0
        self.line = 1

        while self.pos < len(self.src):

            # --- indentation at start of each line ---------------------
            if self.pos == 0 or self.src[self.pos - 1] == "\n":
                line_start = self.pos
                while self.pos < len(self.src) and self.src[self.pos] == " ":
                    self.pos += 1

                # skip blank lines and comment-only lines
                rest = self.src[self.pos:]
                if not rest or rest[0] == "\n" or rest.startswith("#"):
                    while self.pos < len(self.src) and self.src[self.pos] != "\n":
                        self.pos += 1
                    if self.pos < len(self.src):
                        self.pos += 1
                        self.line += 1
                    continue

                indent_level = self.pos - line_start
                self.handle_indent(indent_level)

            ch = self.peek()

            # newline
            if ch == "\n":
                self.advance()
                self.add(NEWLINE)
                continue

            if ch == "\r":
                self.advance()
                continue

            # whitespace
            if ch in (" ", "\t"):
                self.advance()
                continue

            # comment
            if ch == "#":
                while self.pos < len(self.src) and self.peek() != "\n":
                    self.advance()
                continue

            # f-strings: f"..." or f'...'
            if ch == "f" and self.peek(1) in ('"', "'"):
                self.advance()        # consume 'f'
                q = self.advance()    # consume opening quote
                if self.peek() == q and self.peek(1) == q:
                    self.advance()    # consume second quote
                    self.advance()    # consume third quote
                    s = self.scan_triple_string(q)
                else:
                    s = self.scan_fstring(q)
                self.add(FSTRING, s)
                continue

            # triple-quoted strings: """...""" or '''...'''
            if ch in ('"', "'") and self.peek(1) == ch and self.peek(2) == ch:
                self.advance()
                self.advance()
                self.advance()
                s = self.scan_triple_string(ch)
                self.add(STRING, s)
                continue

            # string literals
            if ch in ('"', "'"):
                self.advance()
                s = self.scan_string(ch)
                self.add(STRING, s)
                continue

            # numbers
            if ch.isdigit():
                self.tokens.append(self.scan_number(self.advance()))
                continue

            # identifiers / keywords
            if ch.isalpha() or ch == "_":
                self.tokens.append(self.scan_ident_or_keyword(self.advance()))
                continue

            # two-char and one-char operators / delimiters
            self.advance()   # consume ch

            if ch == "+":
                self.add(PLUSEQ  if self.match("=") else PLUS)
            elif ch == "-":
                if self.match(">"):   self.add(ARROW)
                elif self.match("="): self.add(MINUSEQ)
                else:                 self.add(MINUS)
            elif ch == "*":
                if self.match("*"):   self.add(POWER)
                elif self.match("="): self.add(STAREQ)
                else:                 self.add(STAR)
            elif ch == "/":
                if self.match("/"):   self.add(DOUBLESLASH)
                elif self.match("="): self.add(SLASHEQ)
                else:                 self.add(SLASH)
            elif ch == "%":  self.add(PERCENT)
            elif ch == "=":  self.add(EQ   if self.match("=") else ASSIGN)
            elif ch == "!":
                if self.match("="):  self.add(NEQ)
                else: raise LexError(f"Unexpected character '!'", self.line)
            elif ch == "<":  self.add(LTE  if self.match("=") else LT)
            elif ch == ">":  self.add(GTE  if self.match("=") else GT)
            elif ch == "(":  self.add(LPAREN)
            elif ch == ")":  self.add(RPAREN)
            elif ch == "[":  self.add(LBRACKET)
            elif ch == "]":  self.add(RBRACKET)
            elif ch == "{":  self.add(LBRACE)
            elif ch == "}":  self.add(RBRACE)
            elif ch == ":":  self.add(COLON)
            elif ch == ",":  self.add(COMMA)
            elif ch == ".":  self.add(DOT)
            elif ch == "@":  self.add(AT)
            else:
                raise LexError(f"Unexpected character {ch!r}", self.line)

        # Close any open indentation blocks
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.add(DEDENT, 0)

        self.add(EOF)
        return self.tokens


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lex(source: str) -> List[Token]:
    """Tokenize a TypeSht source string. Returns a flat list of Tokens."""
    return Lexer(source).tokenize()