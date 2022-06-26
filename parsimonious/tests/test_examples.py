from types import SimpleNamespace

import pytest

from parsimonious.exceptions import ParseError
from parsimonious.examples.grammar_syntax_extension import AttrsTokenGrammar


def noparse(grammar, text):
    with pytest.raises(ParseError):
        grammar.parse(text)


def test_extended_grammar():
    Tok = SimpleNamespace
    g = AttrsTokenGrammar(r"""
       a = B[@foo=("bar" / "baz") @baz=~"baz"+]
    """)

    assert g.parse([Tok(type="B", foo="bar", baz="bazbaz")])
    assert g.parse([Tok(type="B", foo="baz", baz="bazbaz")])
    noparse(g, [Tok(type="C", foo="bar", baz="baz")])
    noparse(g, [Tok(type="C", foo="bar", baz="baz")])

    g2 = AttrsTokenGrammar(r"""
        segment = TEXT (DATA_SEP TEXT)* SEG_TERM
    """)
    Tok2 = lambda t: SimpleNamespace(type=t)
    tokens = [
        Tok2("TEXT"),
        *([Tok2("DATA_SEP"), Tok2("TEXT")] * 10),
        Tok2("SEG_TERM"),
    ]
    assert g2.parse(tokens)
    SEGMENT_GRAMMAR = AttrsTokenGrammar(r"""
        x12 = segment+
        segment = TEXT (DATA_SEP elem)* SEG_TERM
        elem = value (REPEAT_SEP value)*
        value = TEXT (COMPONENT_SEP TEXT)*
    """)
