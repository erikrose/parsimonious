# -*- coding: utf-8 -*-
import sys
from parsimonious import Grammar, NodeVisitor


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
expression = whitespace variable whitespace assignment_symbol whitespace expression_value whitespace newline?

expression_value = literal_string / identifier_group
identifier_group = (whitespace identifier_value)+
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
newline = "\n"

"""


class BaseStringExpressionNodeVisitor(NodeVisitor):
    def __init__(self, identifiers = None):
        super(BaseStringExpressionNodeVisitor, self).__init__()
        self.identifiers = identifiers or {}

    def visit_literal_string(self, node, visited_children):
        return node.text.strip("'")

    def visit_identifier(self, node, visited_children):
        return node.text

    def visit_variable(self, node, visited_children):
        return node.text

    def visit_expression_value(self, node, visited_children):
        result = ''.join(visited_children)
        return result

    def visit_expression(self, node, visited_children):
        result = [self.visit(child_node) for child_node in node.children]
        result = [item for item in result if item]
        variable_name = result[0]
        expression_value = result[1]
        self.identifiers[variable_name] = expression_value

    def generic_visit(self, node, visited_children):
        pass


class IdentifierGroupNodeVisitor(BaseStringExpressionNodeVisitor):
    def __init__(self, identifiers = None):
        super(IdentifierGroupNodeVisitor, self).__init__()
        self.identifiers = identifiers or {}

    def visit_identifier(self, node, visited_children):
        result = self.identifiers[node.text]
        return result


class StringExpressionNodeVisitor(BaseStringExpressionNodeVisitor):
    def __init__(self, identifiers = None):
        super(StringExpressionNodeVisitor, self).__init__()
        self.identifiers = identifiers or {}

    def visit_identifier_group(self, node, visited_children):
        identifier_group_node_visitor = IdentifierGroupNodeVisitor(identifiers=self.identifiers)
        nodes = []
        for child_node in node.children:
            nodes += child_node.children
        values = [identifier_group_node_visitor.visit(node) for node in nodes]
        values = [value for value in values if value is not None]
        result = ''.join(values)
        return result


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