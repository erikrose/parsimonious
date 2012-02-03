from nose.tools import eq_

from parsimonious.expressions import Regex, Sequence, OneOf, AllOf, Not, Optional, ZeroOrMore


def test_regex():
    eq_(Regex('hello')._match('ehello', 1), 5)  # simple
    eq_(Regex('hello*')._match('hellooo'), 7)  # *
    eq_(Regex('hello*')._match('goodbye'), None)  # no match

def test_sequence():
    eq_(Sequence(Regex('hi*'), Regex('lo'), Regex('.ingo'))._match('hiiiilobingo1234'),
        12)  # succeed
    eq_(Sequence(Regex('hi*'), Regex('lo'), Regex('.ingo'))._match('hiiiilobing'),
        None)  # don't
    eq_(Sequence(Regex('hi*'))._match('>hiiii', 1),
        5)  # non-0 pos

def test_one_of():
    eq_(OneOf(Regex('aaa'), Regex('bb'))._match('aaa'), 3)  # first alternative
    eq_(OneOf(Regex('aaa'), Regex('bb'))._match('bbaaa'), 2)  # second
    eq_(OneOf(Regex('aaa'), Regex('bb'))._match('aa'), None)  # no match

def test_all_of():
    eq_(AllOf(Regex('0'), Regex('..'))._match('01'), 2)  # match
    eq_(AllOf(Regex('0'), Regex('.2'))._match('01'), None)  # don't

def test_not():
    eq_(Not(Regex('.'))._match(''), 0)  # match
    eq_(Not(Regex('.'))._match('Hi'), None)  # don't

def test_optional():
    eq_(Sequence(Optional(Regex('a')), Regex('b'))._match('b'), 1)  # contained expr fails
    eq_(Sequence(Optional(Regex('a')), Regex('b'))._match('ab'), 2)  # contained expr succeeds

def test_zero_or_more():
    eq_(ZeroOrMore(Regex('b'))._match(''), 0)  # zero
    eq_(ZeroOrMore(Regex('b'))._match('bbb'), 3)  # more

    eq_(Regex('^')._match(''), 0)  # Validate the next test.
    eq_(ZeroOrMore(Regex('^'))._match(''), 0)  # Try to make it loop infinitely using a zero-length contained expression.
