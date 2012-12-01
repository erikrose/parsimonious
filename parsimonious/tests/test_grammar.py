from unittest import TestCase

from nose import SkipTest
from nose.tools import eq_, assert_raises, ok_

from parsimonious.exceptions import UndefinedLabel
from parsimonious.nodes import Node
from parsimonious.grammar import dsl_grammar, DslVisitor, Grammar


class BootstrapingGrammarTests(TestCase):
    """Tests for the expressions in the grammar that parses the grammar
    definition syntax"""

    def test_ws(self):
        text = ' \t\r'
        eq_(dsl_grammar['ws'].parse(text), Node('ws', text, 0, 3))

    def test_quantifier(self):
        text = '*'
        eq_(dsl_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))
        text = '?'
        eq_(dsl_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))
        text = '+'
        eq_(dsl_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))

    def test_literal(self):
        text = '"anything but quotes#$*&^"'
        eq_(dsl_grammar['literal'].parse(text), Node('literal', text, 0, len(text)))
        text = r'''r"\""'''
        eq_(dsl_grammar['literal'].parse(text), Node('literal', text, 0, 5))

    def test_regex(self):
        text = '~"[a-zA-Z_][a-zA-Z_0-9]*"LI'
        eq_(dsl_grammar['regex'].parse(text),
            Node('regex', text, 0, len(text), children=[
                 Node('', text, 0, 1),
                 Node('literal', text, 1, 25),
                 Node('', text, 25, 27)]))

    def test_successes(self):
        """Make sure the PEG recognition grammar succeeds on various inputs."""
        ok_(dsl_grammar['label'].parse('_'))
        ok_(dsl_grammar['label'].parse('jeff'))
        ok_(dsl_grammar['label'].parse('_THIS_THING'))

        ok_(dsl_grammar['atom'].parse('some_label'))
        ok_(dsl_grammar['atom'].parse('"some literal"'))
        ok_(dsl_grammar['atom'].parse('~"some regex"i'))

        ok_(dsl_grammar['quantified'].parse('~"some regex"i*'))
        ok_(dsl_grammar['quantified'].parse('thing+'))
        ok_(dsl_grammar['quantified'].parse('"hi"?'))

        ok_(dsl_grammar['term'].parse('this'))
        ok_(dsl_grammar['term'].parse('that+'))

        ok_(dsl_grammar['sequence'].parse('this that? other'))

        ok_(dsl_grammar['ored'].parse('this / that+ / "other"'))

        ok_(dsl_grammar['anded'].parse('this & that+ & "other"'))

        ok_(dsl_grammar['poly_term'].parse('this & that+ & "other"'))
        ok_(dsl_grammar['poly_term'].parse('this / that? / "other"+'))
        ok_(dsl_grammar['poly_term'].parse('this? that other*'))

        ok_(dsl_grammar['rhs'].parse('this'))
        ok_(dsl_grammar['rhs'].parse('this? that other*'))

        ok_(dsl_grammar['rule'].parse('this = that\r'))
        ok_(dsl_grammar['rule'].parse('this = the? that other* \t\r'))
        ok_(dsl_grammar['rule'].parse('the=~"hi*"\n'))

        ok_(dsl_grammar.parse('''
            this = the? that other*
            that = "thing"
            the=~"hi*"
            other = "ahoy hoy"
            '''))


class DslVisitorTests(TestCase):
    """Tests for ``DslVisitor``

    As I write these, Grammar is not yet fully implemented. Normally, there'd
    be no reason to use ``DslVisitor`` directly.

    """
    def test_round_trip(self):
        """Test a simple round trip.

        Parse a simple grammar, turn the parse tree into a map of expressions,
        and use that to parse another piece of text.

        Not everything was implemented yet, but it was a big milestone and a
        proof of concept.

        """
        tree = dsl_grammar.parse('''number = ~"[0-9]+"\n''')
        rules, default_rule = DslVisitor().visit(tree)

        text = '98'
        eq_(default_rule.parse(text), Node('number', text, 0, 2))

    def test_undefined_rule(self):
        """Make sure we throw the right exception on undefined rules."""
        tree = dsl_grammar.parse('boy = howdy\n')
        assert_raises(UndefinedLabel, DslVisitor().visit, tree)

    def test_optional(self):
        tree = dsl_grammar.parse('boy = "howdy"?\n')
        rules, default_rule = DslVisitor().visit(tree)

        howdy = 'howdy'

        # It should turn into a Node from the Optional and another from the
        # Literal within.
        eq_(default_rule.parse(howdy), Node('boy', howdy, 0, 5, children=[
                                          Node('', howdy, 0, 5)]))


class GrammarTests(TestCase):
    """Integration-test ``Grammar``: feed it a PEG and see if it works.

    That the correct ``Expression`` tree is built is already tested in
    ``DslGrammarTests``. This tests only that the ``Grammar`` base class's
    ``_rules_from_dsl`` works.

    """
    def test_rules_from_dsl(self):
        """Test the ``Grammar`` base class's DSL-to-expression-tree
        transformation."""
        greeting_grammar = Grammar('greeting = "hi" / "howdy"')
        tree = greeting_grammar.parse('hi')
        eq_(tree, Node('greeting', 'hi', 0, 2, children=[
                       Node('', 'hi', 0, 2)]))
