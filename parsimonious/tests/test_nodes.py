# -*- coding: utf-8 -*-
from nose import SkipTest
from nose.tools import eq_, assert_raises

from parsimonious import Grammar, NodeVisitor, VisitationError, rule
from parsimonious.nodes import Node


class HtmlFormatter(NodeVisitor):
    """Visitor that turns a parse tree into HTML fragments"""

    grammar = Grammar("""bold_open  = '(('""")  # just partial

    def visit_bold_open(self, node, visited_children):
        return '<b>'

    def visit_bold_close(self, node, visited_children):
        return '</b>'

    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text

    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)


class ExplosiveFormatter(NodeVisitor):
    """Visitor which raises exceptions"""

    def visit_boom(self, node, visited_children):
        raise ValueError


def test_visitor():
    """Assert a tree gets visited correctly.

    We start with a tree from applying this grammar... ::

        bold_text  = bold_open text bold_close
        text       = ~'[a-zA-Z 0-9]*'
        bold_open  = '(('
        bold_close = '))'

    ...to this text::

        ((o hai))

    """
    text = '((o hai))'
    tree = Node('bold_text', text, 0, 9,
                [Node('bold_open', text, 0, 2),
                 Node('text', text, 2, 7),
                 Node('bold_close', text, 7, 9)])
    result = HtmlFormatter().visit(tree)
    eq_(result, '<b>o hai</b>')


def test_visitation_exception():
    assert_raises(VisitationError,
                  ExplosiveFormatter().visit,
                  Node('boom', '', 0, 0))


def test_str():
    """Test str and unicode of ``Node``."""
    n = Node('text', 'o hai', 0, 5)
    good = '<Node called "text" matching "o hai">'
    eq_(str(n), good)


def test_repr():
    """Test repr of ``Node``."""
    s = u'hai ö'
    boogie = u'böogie'
    n = Node(boogie, s, 0, 3, children=[
            Node('', s, 3, 4), Node('', s, 4, 5)])
    eq_(repr(n), """s = {hai_o}\nNode({boogie}, s, 0, 3, children=[Node('', s, 3, 4), Node('', s, 4, 5)])""".format(hai_o=repr(s), boogie=repr(boogie)))


def test_parse_shortcut():
    """Exercise the simple case in which the visitor takes care of parsing."""
    eq_(HtmlFormatter().parse('(('), '<b>')


def test_match_shortcut():
    """Exercise the simple case in which the visitor takes care of matching."""
    eq_(HtmlFormatter().match('((other things'), '<b>')


class CoupledFormatter(NodeVisitor):
    @rule('bold_open text bold_close')
    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)

    @rule('"(("')
    def visit_bold_open(self, node, visited_children):
        return '<b>'

    @rule('"))"')
    def visit_bold_close(self, node, visited_children):
        return '</b>'

    @rule('~"[a-zA-Z 0-9]*"')
    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text


def test_rule_decorator():
    """Make sure the @rule decorator works."""
    eq_(CoupledFormatter().parse('((hi))'), '<b>hi</b>')


def test_rule_decorator_subclassing():
    """Make sure we can subclass and override visitor methods without blowing
    away the rules attached to them."""
    class OverridingFormatter(CoupledFormatter):
        def visit_text(self, node, visited_children):
            """Return the text capitalized."""
            return node.text.upper()

        @rule('"not used"')
        def visit_useless(self, node, visited_children):
            """Get in the way. Tempt the metaclass to pave over the
            superclass's grammar with a new one."""

    raise SkipTest("I haven't got around to making this work yet.")
    eq_(OverridingFormatter().parse('((hi))'), '<b>HI</b>')


class PrimalScream(Exception):
    pass


def test_unwrapped_exceptions():
    class Screamer(NodeVisitor):
        grammar = Grammar("""greeting = 'howdy'""")
        unwrapped_exceptions = (PrimalScream,)

        def visit_greeting(self, thing, visited_children):
            raise PrimalScream('This should percolate up!')

    assert_raises(PrimalScream, Screamer().parse, 'howdy')
