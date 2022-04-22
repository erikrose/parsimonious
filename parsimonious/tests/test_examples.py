from types import SimpleNamespace

import pytest

from parsimonious.exceptions import ParseError
from parsimonious.examples.grammar_syntax_extension import AttrsTokenGrammar


def noparse(grammar, text):
    with pytest.raises(ParseError):
        grammar.parse(text)


def test_extended_grammar():
    g = AttrsTokenGrammar(r"""
       a = B[@foo=("bar" / "baz") @baz=~"baz"+]
    """)

    assert g.parse([SimpleNamespace(type="B", foo="bar", baz="bazbaz")])
    assert g.parse([SimpleNamespace(type="B", foo="baz", baz="bazbaz")])
    noparse(g, [SimpleNamespace(type="C", foo="bar", baz="baz")])
    noparse(g, [SimpleNamespace(type="C", foo="bar", baz="baz")])