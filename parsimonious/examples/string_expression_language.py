# -*- coding: utf-8 -*-
import sys
from parsimonious import Grammar


string_expression_grammar = r"""

program = program_body / ignored_line*
program_body = ignored_line* begin line* end ignored_line*
ignored_line = comment_line / blank_line
comment_body = whitespace comment_symbol comment_text
comment_line = comment_body newline
blank_line = whitespace newline
line = expression / ignored_line

begin = whitespace begin_symbol whitespace
end = whitespace end_symbol whitespace
expression = whitespace identifier whitespace assignment_symbol whitespace expression_value whitespace newline?

expression_value = identifier_group / literal_string
identifier_group = (whitespace identifier)+
literal_string = ~"'.*'"
comment_text = ~".*"
identifier = ~"[a-zA-Z0-9_]+"
single_whitespace = ~"[ \t]"
whitespace = single_whitespace*

begin_symbol = "{"
end_symbol = "}"
comment_symbol = "#"
assignment_symbol = "="
newline = "\n"

"""


class StringExpressionLanguage(object):
    def __init__(self):
        self._grammar = Grammar(string_expression_grammar)


    def evaluate(self, text):
        nodes = self._grammar.parse(text)
        print nodes

    def main(self):
        filename = sys.argv[1]
        with open(filename) as file:
            contents = file.read()
        print self.evaluate(contents)


if __name__ == "__main__":
    StringExpressionLanguage().main()