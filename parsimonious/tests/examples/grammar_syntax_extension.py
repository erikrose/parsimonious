"""
This example extends parsimonious's grammar syntax for a different approach to token grammars:
* CAPITALIZED references are refer to ``token.type`` names. They do not need to be explicitly
  named elsewhere in the grammar.
* lowercase references are refer to other rules.
* A token's attributes can match rules, e.g. requiring that an attribute be a date in a particular
  format. This uses a syntax similar to Xpath's ``node[@attr='value']`` syntax.
"""

from typing import Dict

from parsimonious.grammar import Grammar
from parsimonious.expressions import Expression
from parsimonious.nodes import Node


class TokenRef(Expression):
    def __init__(self, ref, name=""):
        super().__init__(name=name)
        self.ref = ref

    def _uncached_match(self, token_list, pos, cache, error):
        if self.ref == getattr(token_list[pos], "type", None):
            return Node(self, token_list, pos, pos + 1, children=[])


class AttrsPredicateExpression(Expression):
    """
    A predicate expression that matches a node with a given set of attributes.
    """

    def __init__(self, token_type, attrs: Dict[str, str]):
        self.attrs = attrs
        self.token_type = token_type

    def __repr__(self) -> str:
        return f"AttrsPredicateExpression({self.token_type}[{self.attrs}])" % self.attrs

    def _uncached_match(self, token_list, pos, cache, error):

        tok_match = self.token_type.match_core(token_list, pos, cache, error)
        if tok_match:
            tok = token_list[pos]
            for k, v in self.attrs.items():
                attr = getattr(tok, k, None)
                if not isinstance(attr, str) or not v.parse(attr):
                    return None
            # TODO: should children have each of the attr matches?
            return Node(self, token_list, pos, pos+1, children=[tok_match])


class AttrsTokenGrammar(Grammar):
    rule_grammar = Grammar.rule_grammar.extend(r"""
        # TODO: Support lexer natively?
        term = attrs_predicate_expression / ^term

        # Token names are required to be all-caps alphanumeric, with underscores.
        reference = token_reference / ^reference
        token_reference = ~r"[A-Z_][A-Z0-9_]*"

        attrs_predicate_expression = token_reference "[" _ attr_expressions "]" _
        attr_expressions = ("@" label "=" _ expression _)+
    """)

    class visitor_cls(Grammar.visitor_cls):
        def visit_token_reference(self, node, children) -> str:
            return TokenRef(node.text)

        def visit_attrs_predicate_expression(self, node, children):
            label, _, lbrac,  attr_expressions, rbrac, _ = children
            return AttrsPredicateExpression(label, attr_expressions)

        def visit_attr_expressions(self, node, children) -> Dict[str, Expression]:
            predicates = {}
            for at, label, equals, _, expression, _ in children:
                assert isinstance(label, str)
                predicates[label] = expression
            return predicates
