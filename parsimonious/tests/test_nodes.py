from nose.tools import eq_

from parsimonious.nodes import Node, NodeVisitor


class HtmlFormatter(NodeVisitor):
    """Visitor that turns a parse tree into HTML fragments"""
    def visit_bold_open(self, node, visited_children):
        return '<b>'

    def visit_bold_close(self, node, visited_children):
        return '</b>'

    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text

    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)


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


def test_repr():
    """Test repr, str, and unicode of ``Node``."""
    n = Node('text', 'o hai', 0, 5)
    eq_(str(n), '<Node called "text" matching "o hai">')
    eq_(unicode(n), '<Node called "text" matching "o hai">')
    eq_(repr(n), '<Node called "text" matching "o hai">')
