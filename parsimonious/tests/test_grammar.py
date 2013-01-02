from unittest import TestCase

from nose import SkipTest
from nose.tools import eq_, assert_raises, ok_

from parsimonious.exceptions import UndefinedLabel, BadGrammar
from parsimonious.nodes import Node
from parsimonious.grammar import rule_grammar, RuleVisitor, Grammar


class BootstrapingGrammarTests(TestCase):
    """Tests for the expressions in the grammar that parses the grammar
    definition syntax"""

    def test_ws(self):
        text = ' \t\r'
        eq_(rule_grammar['ws'].parse(text), Node('ws', text, 0, 3))

    def test_quantifier(self):
        text = '*'
        eq_(rule_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))
        text = '?'
        eq_(rule_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))
        text = '+'
        eq_(rule_grammar['quantifier'].parse(text), Node('quantifier', text, 0, 1))

    def test_literal(self):
        text = '"anything but quotes#$*&^"'
        eq_(rule_grammar['literal'].parse(text), Node('literal', text, 0, len(text)))
        text = r'''r"\""'''
        eq_(rule_grammar['literal'].parse(text), Node('literal', text, 0, 5))

    def test_regex(self):
        text = '~"[a-zA-Z_][a-zA-Z_0-9]*"LI'
        eq_(rule_grammar['regex'].parse(text),
            Node('regex', text, 0, len(text), children=[
                 Node('', text, 0, 1),
                 Node('literal', text, 1, 25),
                 Node('', text, 25, 27)]))

    def test_successes(self):
        """Make sure the PEG recognition grammar succeeds on various inputs."""
        ok_(rule_grammar['label'].parse('_'))
        ok_(rule_grammar['label'].parse('jeff'))
        ok_(rule_grammar['label'].parse('_THIS_THING'))

        ok_(rule_grammar['atom'].parse('some_label'))
        ok_(rule_grammar['atom'].parse('"some literal"'))
        ok_(rule_grammar['atom'].parse('~"some regex"i'))

        ok_(rule_grammar['quantified'].parse('~"some regex"i*'))
        ok_(rule_grammar['quantified'].parse('thing+'))
        ok_(rule_grammar['quantified'].parse('"hi"?'))

        ok_(rule_grammar['term'].parse('this'))
        ok_(rule_grammar['term'].parse('that+'))

        ok_(rule_grammar['sequence'].parse('this that? other'))

        ok_(rule_grammar['ored'].parse('this / that+ / "other"'))

        # + is higher precedence than &, so 'anded' should match the whole
        # thing:
        ok_(rule_grammar['lookahead_term'].parse('&this+'))

        ok_(rule_grammar['expression'].parse('this'))
        ok_(rule_grammar['expression'].parse('this? that other*'))
        ok_(rule_grammar['expression'].parse('&this / that+ / "other"'))
        ok_(rule_grammar['expression'].parse('this / that? / "other"+'))
        ok_(rule_grammar['expression'].parse('this? that other*'))

        ok_(rule_grammar['rule'].parse('this = that\r'))
        ok_(rule_grammar['rule'].parse('this = the? that other* \t\r'))
        ok_(rule_grammar['rule'].parse('the=~"hi*"\n'))

        ok_(rule_grammar.parse('''
            this = the? that other*
            that = "thing"
            the=~"hi*"
            other = "ahoy hoy"
            '''))


class RuleVisitorTests(TestCase):
    """Tests for ``RuleVisitor``

    As I write these, Grammar is not yet fully implemented. Normally, there'd
    be no reason to use ``RuleVisitor`` directly.

    """
    def test_round_trip(self):
        """Test a simple round trip.

        Parse a simple grammar, turn the parse tree into a map of expressions,
        and use that to parse another piece of text.

        Not everything was implemented yet, but it was a big milestone and a
        proof of concept.

        """
        tree = rule_grammar.parse('''number = ~"[0-9]+"\n''')
        rules, default_rule = RuleVisitor().visit(tree)

        text = '98'
        eq_(default_rule.parse(text), Node('number', text, 0, 2))

    def test_undefined_rule(self):
        """Make sure we throw the right exception on undefined rules."""
        tree = rule_grammar.parse('boy = howdy\n')
        assert_raises(UndefinedLabel, RuleVisitor().visit, tree)

    def test_optional(self):
        tree = rule_grammar.parse('boy = "howdy"?\n')
        rules, default_rule = RuleVisitor().visit(tree)

        howdy = 'howdy'

        # It should turn into a Node from the Optional and another from the
        # Literal within.
        eq_(default_rule.parse(howdy), Node('boy', howdy, 0, 5, children=[
                                           Node('', howdy, 0, 5)]))


class GrammarTests(TestCase):
    """Integration-test ``Grammar``: feed it a PEG and see if it works."""

    def test_expressions_from_rules(self):
        """Test the ``Grammar`` base class's ability to compile an expression
        tree from rules.

        That the correct ``Expression`` tree is built is already tested in
        ``RuleGrammarTests``. This tests only that the ``Grammar`` base class's
        ``_expressions_from_rules`` works.

        """
        greeting_grammar = Grammar('greeting = "hi" / "howdy"')
        tree = greeting_grammar.parse('hi')
        eq_(tree, Node('greeting', 'hi', 0, 2, children=[
                       Node('', 'hi', 0, 2)]))

    def test_unicode(self):
        """Assert that a ``Grammar`` can convert into a string-formatted series
        of rules."""
        grammar = Grammar(r"""
                          bold_text  = bold_open text bold_close
                          text       = ~"[A-Z 0-9]*"i
                          bold_open  = "(("
                          bold_close = "))"
                          """)
        lines = unicode(grammar).splitlines()
        eq_(lines[0], 'bold_text = bold_open text bold_close')
        ok_('text = ~"[A-Z 0-9]*"i' in lines)
        ok_('bold_open = "(("' in lines)
        ok_('bold_close = "))"' in lines)
        eq_(len(lines), 4)

    def test_match(self):
        """Make sure partial-matching (with pos) works."""
        grammar = Grammar(r"""
                          bold_text  = bold_open text bold_close
                          text       = ~"[A-Z 0-9]*"i
                          bold_open  = "(("
                          bold_close = "))"
                          """)
        s = ' ((boo))yah'
        eq_(grammar.match(s, pos=1), Node('bold_text', s, 1, 8, children=[
                                         Node('bold_open', s, 1, 3),
                                         Node('text', s, 3, 6),
                                         Node('bold_close', s, 6, 8)]))

    def test_bad_grammar(self):
        """Constructing a Grammar with bad rules should raise BadGrammar."""
        assert_raises(BadGrammar, Grammar, 'just a bunch of junk')

    def test_comments(self):
        """Test tolerance of comments and blank lines in and around rules."""
        grammar = Grammar(r"""# This is a grammar.

                          # It sure is.
                          bold_text  = stars text stars  # nice
                          text       = ~"[A-Z 0-9]*"i #dude
                          
                          
                          stars      = "**"
                          # Pretty good
                          #Oh yeah.#""")  # Make sure a comment doesn't need a
                                          # \n or \r to end.
        eq_(str(grammar), '''bold_text = stars text stars\n'''
                          '''text = ~"[A-Z 0-9]*"i\n'''
                          '''stars = "**"''')

    def test_not(self):
        """Make sure "not" predicates get parsed and work properly."""
        grammar = Grammar(r'''not_arp = !"arp" ~"[a-z]+"''')
        eq_(grammar.parse('arp'), None)
        ok_(grammar.parse('argle') is not None)

    def test_lookahead(self):
        grammar = Grammar(r'''starts_with_a = &"a" ~"[a-z]+"''')
        eq_(grammar.parse('burp'), None)

        s = 'arp'
        eq_(grammar.parse('arp'), Node('starts_with_a', s, 0, 3, children=[
                                      Node('', s, 0, 0),
                                      Node('', s, 0, 3)]))

    def test_parens(self):
        grammar = Grammar(r'''sequence = "chitty" (" " "bang")+''')
        # Make sure it's not as if the parens aren't there:
        eq_(grammar.parse('chitty bangbang'), None)

        s = 'chitty bang bang'
        eq_(str(grammar.parse(s)),
            """<Node called "sequence" matching "chitty bang bang">
    <Node matching "chitty">
    <Node matching " bang bang">
        <Node matching " bang">
            <Node matching " ">
            <Node matching "bang">
        <Node matching " bang">
            <Node matching " ">
            <Node matching "bang">""")
