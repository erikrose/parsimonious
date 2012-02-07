from nose.tools import eq_

from parsimonious.nodes import Node, NodeVisitor


class HtmlFormatter(NodeVisitor):
    """Visitor that turns a parse tree into HTML fragments"""
    def visit_bold_open(self, node):
        return '<b>'

    def visit_bold_close(self, node):
        return '</b>'

    def visit_text(self, node):
        """Return the text verbatim."""
        return node.text

    def visit_bold_text(self, node):
        return ''.join(self.visit(n) for n in node.children)


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
    eq_(str(n), '<text "o hai">')
    eq_(unicode(n), '<text "o hai">')
    eq_(repr(n), '<text "o hai">')
