from collections import OrderedDict
import importlib
import sys
from xml.etree import ElementTree

import pytest

from parsimonious.expressions import Literal, OneOf, Quantifier, Sequence
from parsimonious.grammar import Grammar, TokenGrammar, rule_grammar


def convert(grammar, **options):
    pytest.importorskip('railroad')
    from parsimonious.diagrams import convert_grammar_to_diagram
    return convert_grammar_to_diagram(grammar, **options)


def labels(svg):
    root = ElementTree.fromstring(svg)
    return [item.text for item in root.iter('{http://www.w3.org/2000/svg}text')]


def test_standalone_svg_is_ordered_deterministic_and_does_not_change_grammar():
    grammar = Grammar('start = word "!"\nword = ~"[a-z]+"')
    before = str(grammar)
    expressions = list(grammar.values())
    output = convert(grammar)
    assert isinstance(output, OrderedDict)
    assert list(output) == ['start', 'word']
    for svg in output.values():
        assert isinstance(svg, bytes)
        root = ElementTree.fromstring(svg)
        assert root.tag == '{http://www.w3.org/2000/svg}svg'
        assert float(root.attrib['width']) > 0
        assert float(root.attrib['height']) > 0
        assert root.find('{http://www.w3.org/2000/svg}style') is not None
    assert convert(grammar) == output
    assert str(grammar) == before
    assert all(a is b for a, b in zip(grammar.values(), expressions))
    assert grammar.parse('hello!').text == 'hello!'


def test_references_and_selected_expansion():
    grammar = Grammar('start = pair pair\npair = letter digit\nletter = "a"\ndigit = "1"')
    assert labels(convert(grammar)['start']) == ['pair', 'pair']
    expanded = convert(grammar, collapsible=['pair'])
    assert labels(expanded['start']) == ['letter', 'digit', 'letter', 'digit']
    assert list(expanded) == list(grammar)
    fully = convert(grammar, collapsible=(name for name in ['pair', 'letter', 'digit']))
    assert labels(fully['start']) == ["'a'", "'1'", "'a'", "'1'"]


def test_direct_recursion_is_a_reference_even_when_collapsible():
    grammar = Grammar('start = "(" start ")" / "x"')
    for options in ({}, {'collapsible': ['start']}):
        result = labels(convert(grammar, **options)['start'])
        assert result == ["'('", 'start', "')'", "'x'", 'ordered choice']


def test_mutual_recursion_stops_at_active_reference():
    grammar = Grammar('start = "a" tail\ntail = start?')
    result = convert(grammar, collapsible=['start', 'tail'])
    assert 'start' in labels(result['start'])
    assert 'tail' in labels(result['tail'])
    assert max(map(len, result.values())) < 10000


def test_aliases_keep_rule_order_and_canonical_references():
    grammar = Grammar('alias = word\nstart = alias word\nword = "hi"')
    output = convert(grammar)
    assert list(output) == ['alias', 'start', 'word']
    assert labels(output['alias']) == ["'hi'"]
    assert labels(output['start']) == ['word', 'word']
    assert labels(convert(grammar, collapsible=['alias'])['start']) == ["'hi'", "'hi'"]


@pytest.mark.parametrize('literal', ['<script>&"\'text', '雪', '\x00\n\t', b'\x00\xff'])
def test_literal_labels_are_xml_escaped_and_represent_bytes_and_controls(literal):
    grammar = Grammar(start=Literal(literal))
    svg = convert(grammar)['start']
    assert labels(svg) == [repr(literal)]
    assert b'<script>' not in svg


def test_token_grammar_labels_token_types():
    grammar = TokenGrammar('start = "NAME" "PLUS" "NAME"')
    svg = convert(grammar)['start']
    assert labels(svg) == ["'NAME'", "'PLUS'", "'NAME'"]
    assert b'token type' in svg


def test_regex_preserves_pattern_and_flags():
    grammar = Grammar('start = ~"[a-z]+"im')
    assert labels(convert(grammar)['start']) == ["~'[a-z]+'imu"]


def test_lookahead_is_labelled_as_zero_width():
    grammar = Grammar('start = &"a" !"b" "a"')
    result = labels(convert(grammar)['start'])
    assert 'lookahead (zero-width)' in result
    assert 'negative lookahead (zero-width)' in result
    assert result.count("'a'") == 2


@pytest.mark.parametrize('suffix, count_label', [
    ('?', None), ('*', None), ('+', None), ('{1}', None),
    ('{2}', 'repeat 2 times'), ('{2,4}', 'repeat 2..4 times'),
    ('{0,4}', 'repeat 0..4 times'), ('{3,}', 'repeat 3 or more times'),
])
def test_repetition_forms(suffix, count_label):
    result = labels(convert(Grammar('start = "x"' + suffix))['start'])
    assert result.count("'x'") == 1
    if count_label:
        assert count_label in result


def test_large_bounds_do_not_expand_each_occurrence():
    svg = convert(Grammar('start = "x"{1000000,2000000}'))['start']
    assert len(svg) < 10000
    assert 'repeat 1000000..2000000 times' in labels(svg)


@pytest.mark.parametrize('expression', [Literal(''), Sequence(), Quantifier(Literal('x'), max=0)])
def test_epsilon_expressions_are_empty_paths(expression):
    assert labels(convert(Grammar(start=expression))['start']) == []


def test_empty_choice_is_not_shown_as_epsilon():
    assert labels(convert(Grammar(start=OneOf()))['start']) == ['never matches']


def test_custom_parser_is_opaque_and_never_called():
    def custom(text, pos):
        raise AssertionError('custom parser was executed')
    svg = convert(Grammar(start=custom))['start']
    assert labels(svg) == ['start']
    assert b'custom parser (opaque)' in svg


def test_empty_grammar_has_no_diagrams():
    assert convert(Grammar()) == OrderedDict()


def test_bootstrap_grammar_renders_every_rule():
    diagrams = convert(rule_grammar)
    assert list(diagrams) == list(rule_grammar)
    for svg in diagrams.values():
        ElementTree.fromstring(svg)


def test_optional_dependency_is_lazy_and_has_actionable_error(monkeypatch):
    monkeypatch.setitem(sys.modules, 'railroad', None)
    module = importlib.import_module('parsimonious.diagrams')
    importlib.reload(module)
    assert Grammar('start = "x"').parse('x').text == 'x'
    with pytest.raises(ImportError, match=r'parsimonious\[railroad\]'):
        module.convert_grammar_to_diagram(Grammar('start = "x"'))


@pytest.mark.parametrize('options, exception', [
    ({'engine': 'syntrax'}, ValueError),
    ({'collapsible': ['missing']}, ValueError),
    ({'collapsible': 'start'}, TypeError),
])
def test_invalid_options(options, exception):
    with pytest.raises(exception):
        convert(Grammar('start = "x"'), **options)


def test_invalid_repetition_bounds():
    with pytest.raises(ValueError, match='bounds'):
        convert(Grammar(start=Quantifier(Literal('x'), min=3, max=2)))


def test_invalid_grammar():
    with pytest.raises(TypeError, match='Grammar'):
        convert({'start': Literal('x')})
