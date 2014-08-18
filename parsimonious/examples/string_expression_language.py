#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from parsimonious import Grammar, NodeVisitor

"""

This is a demonstration of a small domain-specific language
for building strings up out of other strings.

You can define variables that are equal to literal strings or
built up out of other variables.

Evaluating a program will return a dictionary of all the
variables expanded into their full strings.

Variables are evaluated in order, so redefining one
will overwrite the previous definition.

Comments start with a hash character ('#').

For example:

    {
        # test program
        a = "xyz"
        b = "abc"
        c = "def"
        c = "333"    # overwrites def
        d = c + a + b
    }

This would return a python dictionary:

{ "a" : "xyz", b: "abc", c: "333", d: "333xyzabc" }


"""


string_expression_grammar = r"""

program = program_body / ignored_line*
program_body = ignored_line* begin line* end ignored_line*
ignored_line = comment_line / blank_line
comment_body = whitespace comment_symbol comment_text
comment_line = comment_body newline
blank_line = whitespace newline?
line = expression / ignored_line

begin = whitespace begin_symbol whitespace
end = whitespace end_symbol whitespace
plus = whitespace plus_symbol whitespace
expression = whitespace variable whitespace assignment_symbol whitespace expression_value whitespace newline?

expression_value = literal_string / identifier_group
identifier_group = identifier_value (plus identifier_value)*
literal_string = ~"'.*'"
comment_text = ~".*"
variable = identifier
identifier_value = identifier
identifier = ~"[a-zA-Z0-9_]+"
single_whitespace = ~"[ \t]"
whitespace = single_whitespace*

begin_symbol = "{"
end_symbol = "}"
comment_symbol = "#"
assignment_symbol = "="
plus_symbol = "+"
newline = "\n"

"""


class IdentifierGroupNodeVisitor(object):
    def __init__(self, identifiers=None):
        super(IdentifierGroupNodeVisitor, self).__init__()
        self.identifiers = identifiers or {}

    def visit_identifier(self, node):
        result = self.identifiers[node.text]
        return result

    def visit(self, node):
        values = self.collect_matching_children(node, "identifier")
        return ''.join(values)

    def collect_matching_children(self, node, expr_name):
        if node.expr_name == expr_name:
            return self.visit_identifier(node)
        else:
            nodes = []
            if len(node.children) > 0:
                for child_node in node.children:
                    value = self.collect_matching_children(child_node, expr_name)
                    if type(value) != type([]):
                        nodes.append(value)
                    elif len(value) > 0:
                        nodes += value
            return nodes


class StringExpressionNodeVisitor(NodeVisitor):
    def __init__(self, identifiers = None):
        super(StringExpressionNodeVisitor, self).__init__()
        self.identifiers = identifiers or {}

    def visit_literal_string(self, node, visited_children):
        return node.text.strip("'")

    def visit_identifier(self, node, visited_children):
        return node.text

    def visit_variable(self, node, visited_children):
        return node.text

    def visit_expression_value(self, node, visited_children):
        return ''.join(visited_children)

    def visit_expression(self, node, visited_children):
        result = [self.visit(child_node) for child_node in node.children]
        result = [item for item in result if item]
        variable_name = result[0]
        expression_value = result[1]
        self.identifiers[variable_name] = expression_value

    def visit_identifier_group(self, node, visited_children):
        identifier_group_node_visitor = IdentifierGroupNodeVisitor(identifiers=self.identifiers)
        result = identifier_group_node_visitor.visit(node)
        return result

    def generic_visit(self, node, visited_children):
        pass


class StringExpressionLanguage(object):
    def __init__(self):
        self._grammar = Grammar(string_expression_grammar)

    def evaluate(self, text):
        root_node = self._grammar.parse(text)
        node_visitor = StringExpressionNodeVisitor()
        node_visitor.visit(root_node)
        return node_visitor.identifiers

    def main(self):
        filename = sys.argv[1]
        with open(filename) as file:
            contents = file.read()
        print self.evaluate(contents)


if __name__ == "__main__":
    StringExpressionLanguage().main()