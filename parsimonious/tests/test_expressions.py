from nose.tools import eq_

from parsimonious.expressions import Literal, Regex, Sequence, OneOf, AllOf, Not, Optional, ZeroOrMore, OneOrMore
from parsimonious.nodes import Node


def len_eq(node, length):
    """Return whether the match lengths of 2 nodes are equal.

    Makes tests shorter and lets them omit positional stuff they don't care
    about.

    """
    node_length = None if node is None else node.end - node.start
    return node_length == length


# Tests for returning the right lengths:

def test_regex():
    len_eq(Literal('hello').match('ehello', 1), 5)  # simple
    len_eq(Regex('hello*').match('hellooo'), 7)  # *
    len_eq(Regex('hello*').match('goodbye'), None)  # no match
    len_eq(Regex('hello', ignore_case=True).match('HELLO'), 5)

def test_sequence():
    len_eq(Sequence(Regex('hi*'), Literal('lo'), Regex('.ingo')).match('hiiiilobingo1234'),
        12)  # succeed
    len_eq(Sequence(Regex('hi*'), Literal('lo'), Regex('.ingo')).match('hiiiilobing'),
        None)  # don't
    len_eq(Sequence(Regex('hi*')).match('>hiiii', 1),
        5)  # non-0 pos

def test_one_of():
    len_eq(OneOf(Literal('aaa'), Literal('bb')).match('aaa'), 3)  # first alternative
    len_eq(OneOf(Literal('aaa'), Literal('bb')).match('bbaaa'), 2)  # second
    len_eq(OneOf(Literal('aaa'), Literal('bb')).match('aa'), None)  # no match

def test_all_of():
    len_eq(AllOf(Literal('0'), Regex('..')).match('01'), 2)  # match
    len_eq(AllOf(Literal('0'), Regex('.2')).match('01'), None)  # don't

def test_not():
    len_eq(Not(Regex('.')).match(''), 0)  # match
    len_eq(Not(Regex('.')).match('Hi'), None)  # don't

def test_optional():
    len_eq(Sequence(Optional(Literal('a')), Literal('b')).match('b'), 1)  # contained expr fails
    len_eq(Sequence(Optional(Literal('a')), Literal('b')).match('ab'), 2)  # contained expr succeeds

def test_zero_or_more():
    len_eq(ZeroOrMore(Literal('b')).match(''), 0)  # zero
    len_eq(ZeroOrMore(Literal('b')).match('bbb'), 3)  # more

    len_eq(Regex('^').match(''), 0)  # Validate the next test.

    # Try to make it loop infinitely using a zero-length contained expression:
    len_eq(ZeroOrMore(Regex('^')).match(''), 0)

def test_one_or_more():
    len_eq(OneOrMore(Literal('b')).match('b'), 1)  # one
    len_eq(OneOrMore(Literal('b')).match('bbb'), 3)  # more
    len_eq(OneOrMore(Literal('b'), min=3).match('bbb'), 3)  # with custom min; success
    len_eq(OneOrMore(Literal('b'), min=3).match('bb'), None)  # with custom min; failure
    len_eq(OneOrMore(Regex('^')).match('bb'), 0)  # attempt infinite loop



# Tests for building the right trees:

def test_simple_node():
    """Test that leaf expressions like ``Literal`` make the right nodes."""
    h = Literal('hello', name='greeting')
    eq_(h.match('hello'), Node('greeting', 'hello', 0, 5))

def test_sequence_nodes():
    """Assert that ``Sequence`` produces nodes with the right children."""
    s = Sequence(Literal('heigh', name='greeting1'),
                 Literal('ho',    name='greeting2'), name='dwarf')
    text = 'heighho'
    eq_(s.match(text), Node('dwarf', text, 0, 7, children=
                            [Node('greeting1', text, 0, 5),
                             Node('greeting2', text, 5, 7)]))
