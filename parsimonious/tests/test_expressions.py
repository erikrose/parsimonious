#coding=utf-8
from unittest import TestCase

from nose.tools import eq_

from parsimonious.expressions import (Literal, Regex, Sequence, OneOf, Not,
    Optional, ZeroOrMore, OneOrMore, Expression)
from parsimonious.grammar import Grammar, rule_grammar
from parsimonious.nodes import Node


def len_eq(node, length):
    """Return whether the match lengths of 2 nodes are equal.

    Makes tests shorter and lets them omit positional stuff they don't care
    about.

    """
    node_length = None if node is None else node.end - node.start
    return node_length == length


class LengthTests(TestCase):
    """Tests for returning the right lengths

    I wrote these before parse tree generation was implemented. They're
    partially redundant with TreeTests.

    """
    def test_regex(self):
        len_eq(Literal('hello').match('ehello', 1), 5)  # simple
        len_eq(Regex('hello*').match('hellooo'), 7)  # *
        len_eq(Regex('hello*').match('goodbye'), None)  # no match
        len_eq(Regex('hello', ignore_case=True).match('HELLO'), 5)

    def test_sequence(self):
        len_eq(Sequence(Regex('hi*'), Literal('lo'), Regex('.ingo')).match('hiiiilobingo1234'),
            12)  # succeed
        len_eq(Sequence(Regex('hi*'), Literal('lo'), Regex('.ingo')).match('hiiiilobing'),
            None)  # don't
        len_eq(Sequence(Regex('hi*')).match('>hiiii', 1),
            5)  # non-0 pos

    def test_one_of(self):
        len_eq(OneOf(Literal('aaa'), Literal('bb')).match('aaa'), 3)  # first alternative
        len_eq(OneOf(Literal('aaa'), Literal('bb')).match('bbaaa'), 2)  # second
        len_eq(OneOf(Literal('aaa'), Literal('bb')).match('aa'), None)  # no match

    def test_not(self):
        len_eq(Not(Regex('.')).match(''), 0)  # match
        len_eq(Not(Regex('.')).match('Hi'), None)  # don't

    def test_optional(self):
        len_eq(Sequence(Optional(Literal('a')), Literal('b')).match('b'), 1)  # contained expr fails
        len_eq(Sequence(Optional(Literal('a')), Literal('b')).match('ab'), 2)  # contained expr succeeds

    def test_zero_or_more(self):
        len_eq(ZeroOrMore(Literal('b')).match(''), 0)  # zero
        len_eq(ZeroOrMore(Literal('b')).match('bbb'), 3)  # more

        len_eq(Regex('^').match(''), 0)  # Validate the next test.

        # Try to make it loop infinitely using a zero-length contained expression:
        len_eq(ZeroOrMore(Regex('^')).match(''), 0)

    def test_one_or_more(self):
        len_eq(OneOrMore(Literal('b')).match('b'), 1)  # one
        len_eq(OneOrMore(Literal('b')).match('bbb'), 3)  # more
        len_eq(OneOrMore(Literal('b'), min=3).match('bbb'), 3)  # with custom min; success
        len_eq(OneOrMore(Literal('b'), min=3).match('bb'), None)  # with custom min; failure
        len_eq(OneOrMore(Regex('^')).match('bb'), 0)  # attempt infinite loop


class TreeTests(TestCase):
    """Tests for building the right trees

    We have only to test successes here; failures (None-returning cases) are
    covered above.

    """
    def test_simple_node(self):
        """Test that leaf expressions like ``Literal`` make the right nodes."""
        h = Literal('hello', name='greeting')
        eq_(h.match('hello'), Node('greeting', 'hello', 0, 5))

    def test_sequence_nodes(self):
        """Assert that ``Sequence`` produces nodes with the right children."""
        s = Sequence(Literal('heigh', name='greeting1'),
                     Literal('ho',    name='greeting2'), name='dwarf')
        text = 'heighho'
        eq_(s.match(text), Node('dwarf', text, 0, 7, children=
                                [Node('greeting1', text, 0, 5),
                                 Node('greeting2', text, 5, 7)]))

    def test_one_of(self):
        """``OneOf`` should return its own node, wrapping the child that succeeds."""
        o = OneOf(Literal('a', name='lit'), name='one_of')
        text = 'aa'
        eq_(o.match(text), Node('one_of', text, 0, 1, children=[
                                Node('lit', text, 0, 1)]))

    def test_optional(self):
        """``Optional`` should return its own node wrapping the succeeded child."""
        expr = Optional(Literal('a', name='lit'), name='opt')

        text = 'a'
        eq_(expr.match(text), Node('opt', text, 0, 1, children=[
                                   Node('lit', text, 0, 1)]))

        # Test failure of the Literal inside the Optional; the
        # LengthTests.test_optional is ambiguous for that.
        text = ''
        eq_(expr.match(text), Node('opt', text, 0, 0))

    def test_zero_or_more_zero(self):
        """Test the 0 case of ``ZeroOrMore``; it should still return a node."""
        expr = ZeroOrMore(Literal('a'), name='zero')
        text = ''
        eq_(expr.match(text), Node('zero', text, 0, 0))

    def test_one_or_more_one(self):
        """Test the 1 case of ``OneOrMore``; it should return a node with a child."""
        expr = OneOrMore(Literal('a', name='lit'), name='one')
        text = 'a'
        eq_(expr.match(text), Node('one', text, 0, 1, children=[
                                   Node('lit', text, 0, 1)]))

    # Things added since Grammar got implemented are covered in integration
    # tests in test_grammar.


class ParseTests(TestCase):
    """Tests for the ``parse()`` method"""

    def test_parse_success(self):
        """Make sure ``parse()`` returns the tree on success.

        There's not much more than that to test that we haven't already vetted
        above.

        """
        expr = OneOrMore(Literal('a', name='lit'), name='more')
        text = 'aa'
        eq_(expr.parse(text), Node('more', text, 0, 2, children=[
                                   Node('lit', text, 0, 1),
                                   Node('lit', text, 1, 2)]))

    def test_parse_failure(self):
        """Make sure ``parse()`` fails when it doesn't recognize all the way to
        the end."""
        expr = OneOrMore(Literal('a', name='lit'), name='more')
        text = 'aab'
        eq_(expr.parse(text), None)


class RepresentationTests(TestCase):
    """Tests for str(), unicode(), and repr() of expressions"""

    def test_unicode_crash(self):
        """Make sure matched unicode strings don't crash ``__str__``."""
        grammar = Grammar(r'string = ~r"\S+"u')
        str(grammar.parse(u'中文'))
        # Okay, this is passing now, because I commented out __str__ etc. in Node.

    def test_unicode(self):
        """Smoke-test the conversion of expressions to bits of rules.

        A slightly more comprehensive test of the actual values is in
        ``GrammarTests.test_unicode``.

        """
        unicode(rule_grammar)
