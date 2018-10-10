from nose.tools import eq_

from parsimonious import Grammar
from parsimonious.expressions import Regex
from parsimonious.nodes import RegexNode


def test_use_regex_library():
    grammar = Grammar(r'''
    unicode_word = ~"[\p{L}]*"
    ''', use_regex_library=True)
    text = 'Тест'
    expected = RegexNode(expr=Regex(pattern=r'[\p{L}]*', use_regex_library=True), full_text=text, start=0, end=4)
    result = grammar.parse(text=text)
    eq_(result, expected)
