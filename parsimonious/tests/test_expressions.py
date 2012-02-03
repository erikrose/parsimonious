from nose.tools import eq_

from parsimonious.expressions import Regex, Sequence


def test_regex():
    eq_(Regex('hello')._match('ehello', 1, {}), 5)  # simple
    eq_(Regex('hello*')._match('hellooo', 0, {}), 7)  # *
    eq_(Regex('hello*')._match('goodbye', 0, {}), None)  # no match

def test_sequence():
    eq_(Sequence(Regex('hi*'), Regex('lo'), Regex('.ingo'))._match('hiiiilobingo1234', 0, {}),
        12)  # succeed
    eq_(Sequence(Regex('hi*'), Regex('lo'), Regex('.ingo'))._match('hiiiilobing', 0, {}),
        None)  # don't
    eq_(Sequence(Regex('hi*'))._match('>hiiii', 1, {}),
        5)  # non-0 pos
