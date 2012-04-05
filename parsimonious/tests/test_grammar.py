from unittest import TestCase

from nose.tools import eq_, assert_raises

from parsimonious.exceptions import UndefinedLabel
from parsimonious.nodes import Node
from parsimonious.grammar import peg_grammar, PegVisitor


class PegGrammarTests(TestCase):
    """Tests for the expressions in the grammar that parses the grammar definition syntax"""

    def test_ws(self):
        text = ' \t\r'
        eq_(peg_grammar['ws'].parse(text), Node('ws', text, 0, 3))

    def test_quantifier(self):
        text = '*'
        eq_(peg_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))
        text = '?'
        eq_(peg_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))
        text = '+'
        eq_(peg_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))

    def test_literal(self):
        text = '"anything but quotes#$*&^"'
        eq_(peg_grammar['literal'].parse(text), Node('literal', text, 0, len(text)))
        text = r'''r"\""'''
        eq_(peg_grammar['literal'].parse(text), Node('literal', text, 0, 5))

    def test_regex(self):
        text = '~"[a-zA-Z_][a-zA-Z_0-9]*"LI'
        eq_(peg_grammar['regex'].parse(text),
            Node('regex', text, 0, len(text), children=[
                 Node('', text, 0, 1),
                 Node('literal', text, 1, 25),
                 Node('', text, 25, 27)]))

    def test_successes(self):
        """Make sure the PEG recognition grammar succeeds on various inputs."""
        assert peg_grammar['label'].parse('_')
        assert peg_grammar['label'].parse('jeff')
        assert peg_grammar['label'].parse('_THIS_THING')

        assert peg_grammar['atom'].parse('some_label')
        assert peg_grammar['atom'].parse('"some literal"')
        assert peg_grammar['atom'].parse('~"some regex"i')

        assert peg_grammar['quantified'].parse('~"some regex"i*')
        assert peg_grammar['quantified'].parse('thing+')
        assert peg_grammar['quantified'].parse('"hi"?')

        assert peg_grammar['term'].parse('this')
        assert peg_grammar['term'].parse('that+')

        assert peg_grammar['sequence'].parse('this that? other')

        assert peg_grammar['ored'].parse('this / that+ / "other"')

        assert peg_grammar['anded'].parse('this & that+ & "other"')

        assert peg_grammar['poly_term'].parse('this & that+ & "other"')
        assert peg_grammar['poly_term'].parse('this / that? / "other"+')
        assert peg_grammar['poly_term'].parse('this? that other*')

        assert peg_grammar['rhs'].parse('this')
        assert peg_grammar['rhs'].parse('this? that other*')

        assert peg_grammar['rule'].parse('this = that\r')
        assert peg_grammar['rule'].parse('this = the? that other* \t\r')
        assert peg_grammar['rule'].parse('the=~"hi*"\n')

        assert peg_grammar.parse('''
            this = the? that other*
            that = "thing"
            the=~"hi*"
            other = "ahoy hoy"
            ''')


class PegVisitorTests(TestCase):
    """Tests for ``PegVisitor``

    As I write these, Grammar is not yet fully implemented. Normally, there'd
    be no reason to use ``PegVisitor`` directly.

    """
    def test_round_trip(self):
        """Test a simple round trip.

        Parse a simple grammar, turn the parse tree into a map of expressions,
        and use that to parse another piece of text.

        Not everything was implemented yet, but it was a big milestone and a
        proof of concept.

        """
        tree = peg_grammar.parse('''number = ~"[0-9]+"\n''')
        rules, default_rule = PegVisitor().visit(tree)

        text = '98'
        eq_(default_rule.parse(text), Node('number', text, 0, 2))

    def test_undefined_rule(self):
        """Make sure we throw the right exception on undefined rules."""
        tree = peg_grammar.parse('boy = howdy\n')
        assert_raises(UndefinedLabel, PegVisitor().visit, tree)

    def test_optional(self):
        tree = peg_grammar.parse('boy = "howdy"?\n')
        rules, default_rule = PegVisitor().visit(tree)
        
        text = 'howdy'
        eq_(default_rule.parse(text), Node('boy', text, 0, 5, children=[
                                           ]))
