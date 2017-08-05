#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This is a demonstration of a small domain-specific language for building
strings up out of other strings.

You can define variables that are equal to literal strings or built up out of
other variables.

Evaluating a program will return a dictionary of all the variables expanded
into their full strings.

Variables are evaluated in order, so redefining one will overwrite the previous
definition.

Comments start with a hash character ('#').

For example::

    {
        # test program
        a = "xyz"
        b = "abc"
        c = "def"
        c = "333"    # overwrites def
        d = c + a + b
    }

This would return a python dictionary::

    {"a" : "xyz", b: "abc", c: "333", d: "333xyzabc"}

"""
import sys
from parsimonious import Grammar, NodeVisitor


string_expression_grammar = Grammar(r"""
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
    expression = whitespace variable whitespace assignment_symbol whitespace
                 expression_value whitespace newline?

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
    """)


class IdentifierGroupVisitor(NodeVisitor):
    def __init__(self, identifiers=None):
        super(IdentifierGroupVisitor, self).__init__()
        self.identifiers = identifiers or {}

    def visit_identifier(self, node, visited_children):
        return self.identifiers[node.text]

    def visit(self, node):
        values = self.collect_matching_children(node, 'identifier')
        return ''.join(values)

    def collect_matching_children(self, node, expr_name):
        if node.expr_name == expr_name:
            return super(IdentifierGroupVisitor, self).visit(node)
        else:
            nodes = []
            if node.children:
                for child_node in node.children:
                    value = self.collect_matching_children(child_node, expr_name)
                    if type(value) != type([]):
                        nodes.append(value)
                    elif len(value) > 0:
                        nodes += value
            return nodes


class StringExpressionVisitor(NodeVisitor):
    def __init__(self, identifiers = None):
        super(StringExpressionVisitor, self).__init__()
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
        identifier_group_node_visitor = IdentifierGroupVisitor(identifiers=self.identifiers)
        return identifier_group_node_visitor.visit(node)

    def generic_visit(self, node, visited_children):
        pass


def evaluate(string_expressions):
    root_node = string_expression_grammar.parse(string_expressions)
    node_visitor = StringExpressionVisitor()
    node_visitor.visit(root_node)
    return node_visitor.identifiers


def main(self):
    filename = sys.argv[1]
    with open(filename) as file:
        contents = file.read()
    print evaluate(contents)


if __name__ == '__main__':
    main()
