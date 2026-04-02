# TypeSht

A statically-typed programming language that uses Python-like syntax and compiles to TypeScript/JavaScript. Designed for Python developers who want to write type-safe code that runs in JavaScript environments (browsers, Node.js) without learning TypeScript or JavaScript syntax.

> **If it works in Python, it works the same in TypeSht. No surprises.**

---

## Why TypeSht?

Python developers often need to target JavaScript environments — web frontends, Node.js servers, serverless functions. The usual options are:
- Learn JavaScript/TypeScript (steep learning curve)
- Use a transpiler that loses Python semantics (silent bugs)

TypeSht takes a different approach: compile Python-syntax source files to TypeScript, and ship a runtime package (`typesht-runtime`) that preserves Python behavior faithfully in JavaScript environments. Floor division, negative indexing, Python-style dicts, `print()` with `sep`/`end` — it all works exactly as you'd expect.

---

## Requirements

**Compiler:**
- Python 3.10+

**Runtime & output:**
- Node.js 16+
- TypeScript (`npm install -g typescript`)

---

## Installation

**1. Install the TypeSht compiler (Python):**
```bash
pip install typesht
```

**2. Install the TypeSht runtime (Node.js):**
```bash
npm install typesht-runtime
```

---

## Usage

```bash
# Compile to JavaScript (default)
typesht compile myprogram.tsht

# Compile to TypeScript only
typesht compile myprogram.tsht --target ts

# Compile to both JS and TS
typesht compile myprogram.tsht --target both

# Specify output directory
typesht compile myprogram.tsht --output dist/
```

Output goes to an `output/` folder next to your source file by default.

To run the compiled output:

```bash
cd output/
npm init -y
# add "type": "module" to package.json
npm install typesht-runtime
node myprogram.js
```

---

## Language Features

### Variables & Type Annotations

```python
name: str = "Alice"
age: int = 30
score: float = 9.5
is_active: bool = True
x = 42  # untyped
```

### F-Strings

```python
msg: str = f"Hello, {name}! You are {age} years old."
result: str = f"Next year: {age + 1}"
```

### Functions

```python
def greet(name: str, age: int) -> str:
    return f"Hi, I am {name}"

def add(a: int, b: int) -> int:
    return a + b
```

### Lambda Functions

```python
double = lambda x: x * 2
add = lambda x, y: x + y
no_args = lambda: 42
```

### Classes

```python
class Person:
    name: str
    age: int

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def greet(self) -> str:
        return f"Hi, I am {self.name}"

person = Person("Alice", 30)
print(person.greet())
```

### Decorators

```python
class MathHelper:
    @staticmethod
    def add(x: int, y: int) -> int:
        return x + y

    @classmethod
    def create(cls, base: int) -> int:
        return base

    @property
    def value(self) -> int:
        return self._value

# Custom decorators compile to higher-order function calls
@my_decorator
def process(data: str) -> str:
    return data
# → process = myDecorator(process)
```

### Generics

```python
numbers: list[int] = [1, 2, 3]
words: list[str] = ["hello", "world"]
data: dict[str, int] = {"a": 1}

def get_first(items: list[int]) -> int:
    return items[0]
```

### Lists & Dicts

```python
items: list = [10, 20, 30, 40, 50]
print(items[0])     # → 10
print(items[-1])    # → 50  (negative indexing)
print(items[1:3])   # → [20, 30]  (slicing)

data: dict = {"lang": "TypeSht", "version": "0.1"}
```

### Control Flow

```python
if age > 18:
    print("Adult")
elif age == 18:
    print("Just turned 18")
else:
    print("Minor")

for i in range(10):
    print(i)

for item in items:
    print(item)

for k, v in pairs:
    print(f"{k} = {v}")

while x > 0:
    x -= 1
```

### Operators

```python
result = 10 // 3    # floor division → 3
remainder = 10 % 3  # modulo → 1
power = 2 ** 8      # power → 256
x = a and b         # logical and
y = a or b          # logical or
z = not a           # logical not
found = item in items       # membership test
missing = item not in items
```

### Triple-Quoted Strings

```python
msg = """
This is a
multi-line string
"""
```

### Imports

```python
# Standard library (provided by typesht-runtime)
import math
import random
import json
import re
import sys
import os

# With alias
import random as rng

# From imports
from json import dumps, loads
from math import sqrt, pi

# User modules
import mymodule
from mymodule import my_func
```

---

## Standard Library

| Module | Available Functions |
|--------|-------------------|
| `math` | `pi`, `e`, `sqrt`, `floor`, `ceil`, `abs`, `pow`, `log`, `log2`, `log10`, `sin`, `cos`, `tan`, `exp`, `trunc`, `inf`, `nan`, `isnan`, `isinf`, `gcd`, `factorial` |
| `random` | `random`, `randint`, `uniform`, `choice`, `shuffle`, `sample`, `seed` |
| `json` | `dumps`, `loads` |
| `re` | `match`, `search`, `findall`, `sub`, `split`, `compile` |
| `sys` | `argv`, `exit`, `version`, `platform` |
| `os` | `path.join`, `path.dirname`, `path.basename`, `path.abspath`, `path.normpath`, `path.splitext`, `path.split`, `path.exists`, `path.isfile`, `path.isdir`, `path.sep`, `getcwd`, `getenv` |

---

## Type Mappings

| TypeSht | TypeScript |
|---------|------------|
| `str` | `string` |
| `int` | `number` |
| `float` | `number` |
| `bool` | `boolean` |
| `list` | `any[]` |
| `list[int]` | `number[]` |
| `list[str]` | `string[]` |
| `dict` | `any` (backed by `PyDict` runtime class) |
| `None` | `null` |

---

## Python Semantics Preserved

TypeSht ships `typesht-runtime` — an npm package that ensures Python behavior is preserved at runtime:

- `print()` with `sep` and `end` keyword arguments
- Negative indexing on strings and lists (`items[-1]`)
- Slicing on strings and lists (`items[1:3]`)
- Floor division (`//`) toward negative infinity
- Python-style modulo (`%`) for negative numbers
- `dict` with ordered keys and Python iteration behavior (`for k in d`, `.items()`, `.values()`)
- `in` / `not in` membership testing
- Python-style error types (`ValueError`, `TypeError`, `IndexError`, `KeyError`, `ZeroDivisionError`)

---

## Project Structure

```
typesht/
├── src/typesht/       — pip-installable compiler package
│   ├── lexer.py       — Tokenizer
│   ├── parser.py      — AST + Parser
│   ├── codegen.py     — TypeScript code generator
│   └── main.py        — CLI entry point
│
├── compiler/          — Development copy (used by the test runner)
│   ├── lexer.py
│   ├── parser.py
│   ├── codegen.py
│   └── main.py
│
├── runtime/
│   ├── typesht-runtime.ts   — Python behavior runtime (source)
│   └── package.json
│
├── tests/
│   └── test_compiler.py     — 136 compiler unit tests
│
└── examples/
    └── hello.tsht           — Comprehensive example program
```

---

## Running Tests

```bash
python -m pytest tests/
```

---

## Roadmap

- [ ] f-string format specs (`f"{value:.2f}"`)
- [ ] Exception handling (`try` / `except` / `finally`)
- [ ] Multiple inheritance
- [ ] Type aliases
- [ ] Standard library expansion (`itertools`, `functools`, `collections`)
- [ ] Optional JS extras (explicit opt-in JavaScript-specific features)
- [x] Package manager integration (`pip install typesht`, `npm install typesht-runtime`)

---

## Author

Jeiel K Libert

## License

MIT