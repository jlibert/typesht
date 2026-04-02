from src.typesht.lexer import lex
from src.typesht.parser import parse
from src.typesht.codegen import generate

src = """
class Person:
    name: str
    def __init__(self, name: str):
        self.name = name
    def greet(self) -> str:
        return "Hi " + self.name

print(Person("Alice").greet())
"""
print(generate(parse(lex(src))))