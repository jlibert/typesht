# tests/test_compiler.py
# Compiler unit tests for TypeSht

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from lexer import lex
from parser import parse
from codegen import generate


def compile(src: str) -> str:
    """Convenience helper: lex → parse → generate."""
    return generate(parse(lex(src)))


# ── Variables ─────────────────────────────────────────────────────────────────

def test_typed_int():
    assert "let age: number = 25;" in compile("age: int = 25")

def test_typed_str():
    assert 'let name: string = "Alice";' in compile('name: str = "Alice"')

def test_typed_float():
    assert "let score: number = 3.14;" in compile("score: float = 3.14")

def test_typed_bool_true():
    assert "let flag: boolean = true;" in compile("flag: bool = True")

def test_typed_bool_false():
    assert "let flag: boolean = false;" in compile("flag: bool = False")

def test_untyped():
    assert "let x = 42;" in compile("x = 42")

def test_snake_case_to_camel():
    assert "let myVar: number = 1;" in compile("my_var: int = 1")

def test_aug_assign_plus():
    assert "x += 1;" in compile("x = 0\nx += 1")

def test_aug_assign_minus():
    assert "x -= 3;" in compile("x = 10\nx -= 3")


# ── Triple-quoted strings ──────────────────────────────────────────────────────

def test_triple_double_quote():
    assert 'let msg: string = "hello world";' in compile('msg: str = """hello world"""')

def test_triple_single_quote():
    assert 'let msg: string = "hello world";' in compile("msg: str = '''hello world'''")

def test_triple_string_multiline():
    out = compile('msg: str = """line one\nline two"""')
    assert "let msg: string =" in out
    assert "line one" in out
    assert "line two" in out

def test_triple_string_in_print():
    assert '$.print("hello")' in compile('print("""hello""")')


# ── Generics ──────────────────────────────────────────────────────────────────

def test_list_int():
    assert "let items: number[] = [1, 2, 3];" in compile("items: list[int] = [1, 2, 3]")

def test_list_str():
    assert 'let scores: string[] = ["a", "b"];' in compile('scores: list[str] = ["a", "b"]')

def test_list_float():
    assert "let values: number[] = [1.0, 2.0];" in compile("values: list[float] = [1.0, 2.0]")

def test_list_bool():
    assert "let flags: boolean[] = [true, false];" in compile("flags: list[bool] = [True, False]")

def test_dict_generic():
    assert "let data: any =" in compile('data: dict[str, int] = {"a": 1}')

def test_generic_function_param():
    src = """
def get_first(items: list[int]) -> int:
    return items[0]
"""
    assert "function getFirst(items: number[]): number {" in compile(src)

def test_generic_return_type():
    src = """
def get_items() -> list[str]:
    return []
"""
    assert "function getItems(): string[] {" in compile(src)

def test_plain_list_unchanged():
    assert "let items: any[] = [1, 2, 3];" in compile("items: list = [1, 2, 3]")


# ── F-strings ──────────────────────────────────────────────────────────────────

def test_basic_fstring():
    out = compile('name: str = "Alice"\nmsg: str = f"Hello {name}"')
    assert "let msg: string = `Hello ${name}`;" in out

def test_expression_in_fstring():
    out = compile('age: int = 30\nmsg: str = f"Next year: {age + 1}"')
    assert "let msg: string = `Next year: ${age + 1}`;" in out

def test_multiple_interpolations():
    out = compile('name: str = "Alice"\nage: int = 30\nmsg: str = f"Hello {name}, you are {age} years old"')
    assert "let msg: string = `Hello ${name}, you are ${age} years old`;" in out

def test_plain_fstring():
    assert "let msg: string = `just a plain string`;" in compile('msg: str = f"just a plain string"')

def test_fstring_in_print():
    out = compile('name: str = "Alice"\nprint(f"Hello {name}")')
    assert "$.print(`Hello ${name}`)" in out

def test_fstring_arithmetic():
    out = compile('x: int = 5\nmsg: str = f"double: {x * 2}"')
    assert "let msg: string = `double: ${x * 2}`;" in out


# ── Lambdas ────────────────────────────────────────────────────────────────────

def test_lambda_single_param():
    assert "let fn = (x: any) => x * 2;" in compile("fn = lambda x: x * 2")

def test_lambda_multiple_params():
    assert "let add = (x: any, y: any) => x + y;" in compile("add = lambda x, y: x + y")

def test_lambda_no_params():
    assert "let fn = () => 42;" in compile("fn = lambda: 42")

def test_lambda_with_expression():
    assert "let fn = (x: any) => x * x + 1;" in compile("fn = lambda x: x * x + 1")

def test_lambda_as_argument():
    src = """
def apply(fn: any, x: int) -> int:
    return fn(x)

result = apply(lambda x: x * 2, 5)
"""
    assert "(x: any) => x * 2" in compile(src)

def test_lambda_snake_case_param():
    assert "let fn = (myVal: any) => myVal + 1;" in compile("fn = lambda my_val: my_val + 1")


# ── Decorators ─────────────────────────────────────────────────────────────────

def test_decorator_staticmethod():
    src = """
class MathHelper:
    @staticmethod
    def add(x: int, y: int) -> int:
        return x + y
"""
    assert "static add(x: number, y: number): number {" in compile(src)

def test_decorator_classmethod():
    src = """
class Person:
    name: str

    @classmethod
    def create(cls, name: str) -> str:
        return name
"""
    assert "static create(name: string): string {" in compile(src)

def test_decorator_classmethod_drops_cls():
    src = """
class Person:
    @classmethod
    def create(cls, name: str) -> str:
        return name
"""
    assert "cls" not in compile(src)

def test_decorator_property():
    src = """
class Person:
    _name: str

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name
"""
    assert "get name(): string {" in compile(src)

def test_decorator_property_drops_self():
    src = """
class Person:
    _name: str

    @property
    def name(self) -> str:
        return self._name
"""
    out = compile(src)
    assert "get name(): string {" in out
    assert "get name(self)" not in out

def test_decorator_custom_standalone():
    src = """
def my_decorator(fn):
    return fn

@my_decorator
def greet(name: str) -> str:
    return "Hello " + name
"""
    assert "greet = myDecorator(greet);" in compile(src)

def test_decorator_custom_applied_after_function():
    src = """
def my_decorator(fn):
    return fn

@my_decorator
def greet(name: str) -> str:
    return "Hello " + name
"""
    out = compile(src)
    assert out.index("function greet") < out.index("greet = myDecorator")

def test_decorator_multiple_order():
    src = """
@log
@validate
def process(data: str) -> str:
    return data
"""
    out = compile(src)
    assert out.index("process = validate(process)") < out.index("process = log(process)")

def test_decorator_custom_snake_case():
    src = """
@my_decorator
def greet(name: str) -> str:
    return "Hello " + name
"""
    assert "greet = myDecorator(greet);" in compile(src)


# ── Functions ──────────────────────────────────────────────────────────────────

def test_function_simple():
    src = """
def greet(name: str) -> str:
    return "Hello " + name
"""
    out = compile(src)
    assert "function greet(name: string): string {" in out
    assert 'return "Hello " + name;' in out

def test_function_no_return_type():
    src = """
def say_hi():
    print("hi")
"""
    assert "function sayHi(): any {" in compile(src)

def test_function_multiple_params():
    src = """
def add(a: int, b: int) -> int:
    return a + b
"""
    assert "function add(a: number, b: number): number {" in compile(src)

def test_function_bare_call():
    src = """
def greet(name: str) -> str:
    return "Hello " + name

greet("Alice")
"""
    assert 'greet("Alice");' in compile(src)


# ── Classes ────────────────────────────────────────────────────────────────────

def test_class_fields():
    src = """
class Person:
    name: str
    age: int

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
"""
    out = compile(src)
    assert "class Person {" in out
    assert "name: string;" in out
    assert "age: number;" in out
    assert "constructor(name: string, age: number) {" in out
    assert "this.name = name;" in out
    assert "this.age = age;" in out

def test_class_method():
    src = """
class Person:
    name: str

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return "Hi, I am " + self.name
"""
    out = compile(src)
    assert "greet(): string {" in out
    assert 'return "Hi, I am " + this.name;' in out


# ── Class instantiation ────────────────────────────────────────────────────────

def test_class_instantiation_new_keyword():
    src = """
class Person:
    name: str

    def __init__(self, name: str):
        self.name = name

p = Person("Alice")
"""
    assert 'let p = new Person("Alice");' in compile(src)

def test_class_instantiation_user_defined_annotation():
    src = """
class Person:
    name: str

    def __init__(self, name: str):
        self.name = name

p: Person = Person("Alice")
"""
    out = compile(src)
    assert 'let p = new Person("Alice");' in out
    assert out.count("Person(") == 1

def test_class_instantiation_multiple_args():
    src = """
class Point:
    x: int
    y: int

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

pt = Point(1, 2)
"""
    assert "let pt = new Point(1, 2);" in compile(src)

def test_class_instantiation_no_new_for_functions():
    src = """
def greet(name: str) -> str:
    return "Hi " + name

result = greet("Alice")
"""
    out = compile(src)
    assert 'let result = greet("Alice");' in out
    assert "new greet" not in out

def test_class_instantiation_forward_reference():
    src = """
p = Person("Alice")

class Person:
    name: str

    def __init__(self, name: str):
        self.name = name
"""
    assert 'let p = new Person("Alice");' in compile(src)


# ── If / else ──────────────────────────────────────────────────────────────────

def test_if_only():
    src = """
if x > 0:
    print("positive")
"""
    out = compile(src)
    assert "if (x > 0) {" in out
    assert '$.print("positive");' in out

def test_if_else():
    src = """
if x > 0:
    print("positive")
else:
    print("non-positive")
"""
    out = compile(src)
    assert "if (x > 0) {" in out
    assert "} else {" in out

def test_if_elif_else():
    src = """
if x > 0:
    print("positive")
elif x == 0:
    print("zero")
else:
    print("negative")
"""
    out = compile(src)
    assert "if (x > 0) {" in out
    assert "} else if (x === 0) {" in out
    assert "} else {" in out


# ── Loops ──────────────────────────────────────────────────────────────────────

def test_loop_for_range_one_arg():
    src = """
for i in range(10):
    print(i)
"""
    assert "for (let i = 0; i < 10; i += 1) {" in compile(src)

def test_loop_for_range_two_args():
    src = """
for i in range(2, 10):
    print(i)
"""
    assert "for (let i = 2; i < 10; i += 1) {" in compile(src)

def test_loop_for_range_three_args():
    src = """
for i in range(0, 10, 2):
    print(i)
"""
    assert "for (let i = 0; i < 10; i += 2) {" in compile(src)

def test_loop_for_in():
    src = """
for item in items:
    print(item)
"""
    assert "for (const item of items) {" in compile(src)

def test_loop_for_tuple_unpack():
    src = """
for k, v in data:
    print(k)
"""
    assert "for (const [k, v] of data) {" in compile(src)

def test_loop_while():
    src = """
while x > 0:
    x -= 1
"""
    out = compile(src)
    assert "while (x > 0) {" in out
    assert "x -= 1;" in out

def test_loop_break():
    src = """
while True:
    break
"""
    assert "break;" in compile(src)

def test_loop_continue():
    src = """
for i in range(10):
    continue
"""
    assert "continue;" in compile(src)


# ── Print ──────────────────────────────────────────────────────────────────────

def test_print_simple():
    assert '$.print("hello");' in compile('print("hello")')

def test_print_multiple_args():
    assert '$.print("a", "b", "c");' in compile('print("a", "b", "c")')

def test_print_sep():
    assert '{sep: ", "}' in compile('print("a", "b", sep=", ")')

def test_print_end():
    assert '{end: ""}' in compile('print("hello", end="")')


# ── Operators ──────────────────────────────────────────────────────────────────

def test_op_addition():
    assert "1 + 2" in compile("x = 1 + 2")

def test_op_subtraction():
    assert "5 - 3" in compile("x = 5 - 3")

def test_op_multiplication():
    assert "3 * 4" in compile("x = 3 * 4")

def test_op_division():
    assert "10 / 2" in compile("x = 10 / 2")

def test_op_floor_division():
    assert "$.floordiv(10, 3)" in compile("x = 10 // 3")

def test_op_modulo():
    assert "$.pymod(10, 3)" in compile("x = 10 % 3")

def test_op_power():
    assert "Math.pow(2, 8)" in compile("x = 2 ** 8")

def test_op_equality():
    assert "a === b" in compile("x = a == b")

def test_op_inequality():
    assert "a !== b" in compile("x = a != b")

def test_op_less_than():
    assert "a < b" in compile("x = a < b")

def test_op_greater_than():
    assert "a > b" in compile("x = a > b")

def test_op_logical_and():
    assert "a && b" in compile("x = a and b")

def test_op_logical_or():
    assert "a || b" in compile("x = a or b")

def test_op_logical_not():
    assert "!a" in compile("x = not a")

def test_op_in():
    assert "$.contains(b, a)" in compile("x = a in b")

def test_op_not_in():
    assert "!$.contains(b, a)" in compile("x = a not in b")

def test_op_unary_minus():
    assert "-5" in compile("x = -5")


# ── Lists & dicts ──────────────────────────────────────────────────────────────

def test_list_empty():
    assert "let items: any[] = [];" in compile("items: list = []")

def test_list_with_elements():
    assert "let items: any[] = [1, 2, 3];" in compile("items: list = [1, 2, 3]")

def test_list_index():
    assert "$.index(items, 0)" in compile("x = items[0]")

def test_list_negative_index():
    assert "$.index(items, -1)" in compile("x = items[-1]")

def test_list_slice():
    assert "$.slice(items, 1, 3, null)" in compile("x = items[1:3]")

def test_list_slice_no_start():
    assert "$.slice(items, null, 3, null)" in compile("x = items[:3]")

def test_list_slice_no_stop():
    assert "$.slice(items, 1, null, null)" in compile("x = items[1:]")

def test_dict_empty():
    assert "let data: any = $.dict([]);" in compile("data: dict = {}")

def test_dict_with_pairs():
    out = compile('data: dict = {"a": 1, "b": 2}')
    assert 'let data: any = $.dict([["a", 1], ["b", 2]])' in out
    assert "PyDict" not in out


# ── Runtime import ─────────────────────────────────────────────────────────────

def test_runtime_always_imported():
    assert 'import * as $ from "typesht-runtime";' in compile("x: int = 1")


# ── Chained calls ──────────────────────────────────────────────────────────────

def test_chained_method_call():
    src = """
class Person:
    name: str

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return "Hi, I am " + self.name

person = Person("Alice")
print(person.greet())
"""
    assert "person.greet()" in compile(src)

def test_call_result_as_arg():
    src = """
def greet(name: str) -> str:
    return "Hi " + name

print(greet("Alice"))
"""
    assert '$.print(greet("Alice"))' in compile(src)


# ── None & bool ────────────────────────────────────────────────────────────────

def test_none_literal():
    assert "let x = null;" in compile("x = None")

def test_bool_in_while():
    src = """
while True:
    break
"""
    assert "while (true) {" in compile(src)


# ── Comments ───────────────────────────────────────────────────────────────────

def test_comment_is_stripped():
    src = """
# this is a comment
x: int = 1
"""
    out = compile(src)
    assert "#" not in out
    assert "let x: number = 1;" in out


# ── snake_case conversion ──────────────────────────────────────────────────────

def test_snake_case_function_name():
    src = """
def say_hello(first_name: str) -> str:
    return "Hello " + first_name
"""
    assert "function sayHello(firstName: string): string {" in compile(src)

def test_snake_case_variable_in_loop():
    src = """
for my_item in items:
    print(my_item)
"""
    assert "for (const myItem of items) {" in compile(src)


# ── Imports ────────────────────────────────────────────────────────────────────

def test_import_stdlib():
    assert 'import { math } from "typesht-runtime";' in compile("import math")

def test_import_stdlib_with_alias():
    assert 'import { random as rng } from "typesht-runtime";' in compile("import random as rng")

@pytest.mark.parametrize("module", ["math", "random", "json", "re", "sys", "os"])
def test_import_all_stdlib_modules(module):
    assert f'import {{ {module} }} from "typesht-runtime";' in compile(f"import {module}")

def test_import_os():
    assert 'import { os } from "typesht-runtime";' in compile("import os")

def test_os_path_join():
    src = """
import os
p: str = os.path.join("folder", "file.txt")
"""
    assert 'os.path.join("folder", "file.txt")' in compile(src)

def test_os_path_dirname():
    src = """
import os
d: str = os.path.dirname("/some/path/file.txt")
"""
    assert 'os.path.dirname("/some/path/file.txt")' in compile(src)

def test_os_path_splitext():
    src = """
import os
parts = os.path.splitext("file.txt")
"""
    assert 'os.path.splitext("file.txt")' in compile(src)

def test_from_import_stdlib():
    out = compile("from json import dumps, loads")
    assert 'import { json } from "typesht-runtime";' in out
    assert "const dumps = json.dumps;" in out
    assert "const loads = json.loads;" in out

def test_from_import_with_alias():
    assert "const squareRoot = math.sqrt;" in compile("from math import sqrt as square_root")

def test_from_import_single():
    out = compile("from re import findall")
    assert 'import { re } from "typesht-runtime";' in out
    assert "const findall = re.findall;" in out

def test_import_user_module():
    assert 'import * as mymodule from "./mymodule.js";' in compile("import mymodule")

def test_import_user_module_with_alias():
    assert 'import * as m from "./mymodule.js";' in compile("import mymodule as m")

def test_from_import_user_module():
    assert 'import { myFunc } from "./mymodule.js";' in compile("from mymodule import my_func")

def test_from_import_user_module_with_alias():
    assert 'import { myFunc as fn } from "./mymodule.js";' in compile("from mymodule import my_func as fn")

def test_import_snake_case_module():
    assert 'import * as myModule from "./my_module.js";' in compile("import my_module")

def test_stdlib_usage():
    src = """
import math
x: float = math.sqrt(16)
"""
    out = compile(src)
    assert 'import { math } from "typesht-runtime";' in out
    assert "math.sqrt(16)" in out


# ── End-to-end: hello.tsht ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hello_out():
    example_path = os.path.join(os.path.dirname(__file__), "..", "examples", "hello.tsht")
    with open(example_path, "r", encoding="utf-8") as f:
        src = f.read()
    return compile(src)

def test_hello_compiles_without_error(hello_out):
    assert isinstance(hello_out, str)
    assert len(hello_out) > 0

def test_hello_runtime_imported(hello_out):
    assert 'import * as $ from "typesht-runtime";' in hello_out

def test_hello_imports(hello_out):
    assert 'import { math } from "typesht-runtime";' in hello_out
    assert 'import { random } from "typesht-runtime";' in hello_out
    assert 'import { json } from "typesht-runtime";' in hello_out
    assert 'import { os } from "typesht-runtime";' in hello_out

def test_hello_variables(hello_out):
    assert 'let name: string = "Alice";' in hello_out
    assert "let age: number = 30;" in hello_out
    assert "let score: number = 9.5;" in hello_out
    assert "let isActive: boolean = true;" in hello_out

def test_hello_fstring(hello_out):
    assert "`Hello, ${name}! You are ${age} years old.`" in hello_out

def test_hello_lambdas(hello_out):
    assert "let double = (x: any) => x * 2;" in hello_out
    assert "let add = (x: any, y: any) => x + y;" in hello_out

def test_hello_generics(hello_out):
    assert "let numbers: number[] = [1, 2, 3, 4, 5];" in hello_out
    assert 'let words: string[] = ["hello", "world"];' in hello_out
    assert "let scores: number[] = [9.5, 8.0, 7.5];" in hello_out

def test_hello_class(hello_out):
    assert "class Person {" in hello_out
    assert "constructor(name: string, age: number) {" in hello_out
    assert "greet(): string {" in hello_out

def test_hello_decorators(hello_out):
    assert "class MathHelper {" in hello_out
    assert "static add(x: number, y: number): number {" in hello_out
    assert "static create(base: number): number {" in hello_out
    assert "get value(): number {" in hello_out

def test_hello_loops(hello_out):
    assert "for (let i = 0; i < 5; i += 1) {" in hello_out
    assert "for (const item of items) {" in hello_out
    assert "while (x > 0) {" in hello_out

def test_hello_operators(hello_out):
    assert "$.floordiv(10, 3)" in hello_out
    assert "$.pymod(10, 3)" in hello_out
    assert "Math.pow(2, 8)" in hello_out

def test_hello_collections(hello_out):
    assert "let items: any[] = [10, 20, 30, 40, 50];" in hello_out
    assert 'let data: any = $.dict([["lang", "TypeSht"], ["version", "0.1"]])' in hello_out
    assert "PyDict" not in hello_out

def test_hello_stdlib_usage(hello_out):
    assert "math.pi" in hello_out
    assert "math.sqrt(16)" in hello_out
    assert 'os.path.join("folder", "file.txt")' in hello_out
    assert 'os.path.dirname("/some/path/file.txt")' in hello_out