"""Nodes that make up parse trees

Parsing spits out a tree of these, which you can then tell to walk itself and
spit out a useful value. Or you can walk it yourself; the structural attributes
are public.

"""
# TODO: If this is slow, think about using cElementTree or something.
import sys

from parsimonious.exceptions import VisitationException


class Node(object):
    """A parse tree node

    Consider these immutable once constructed. As a side effect of a
    memory-saving strategy in the cache, multiple references to a single
    ``Node`` might be returned in a single parse tree. So, if you started
    messing with one, you'd see surprising parallel changes pop up elsewhere.

    My philosophy is that parse trees (and their nodes) should be
    representation-agnostic. That is, they shouldn't get all mixed up with what
    the final rendered form of a wiki page (or the intermediate representation
    of a programming language, or whatever) is going to be: you should be able
    to parse once and render several representations from the tree, one after
    another.

    """
    # TODO: Make this subclass list. Lower the API mismatch with the language,
    # and watch magic happen.
    __slots__ = ['expr_name',  # The name of the expression that generated me
                 'full_text',  # The full text fed to the parser
                 'start', # The position in the text where that expr started matching
                 'end',   # The position after start where the expr first didn't
                          # match. [start:end] follow Python slice conventions.
                 'children']  # List of child parse tree nodes

    def __init__(self, expr_name, full_text, start, end, children=None):
        self.expr_name = expr_name
        self.full_text = full_text
        self.start = start
        self.end = end
        self.children = children or []

    def prettily(self, error=None):
        """Return a pretty-printed representation of me.

        :arg error: The node to highlight because an error occurred there

        """
        def indent(text):
            return '\n'.join(('    ' + line) for line in text.splitlines())
        ret = [u'<%s "%s">%s' % (self.expr_name or 'Node',
                                 self.text,
                                 '  <-- *** We were here. ***' if error is self else '')]
        for n in self.children:
            ret.append(indent(n.prettily(error=error)))
        return '\n'.join(ret)

    __str__ = __repr__ = __unicode__ = prettily

    def __eq__(self, other):
        """Support by-value deep comparison with other nodes for testing."""
        return (other is not None and
                self.expr_name == other.expr_name and
                self.full_text == other.full_text and
                self.start == other.start and
                self.end == other.end and
                self.children == other.children)

    def __ne__(self, other):
        return not self == other

    @property
    def text(self):
        """Return the text this node matched."""
        return self.full_text[self.start:self.end]


class RegexNode(Node):
    """Node returned from a ``Regex`` expression

    Grants access to the ``re.Match`` object, in case you want to access
    capturing groups, etc.

    """
    __slots__ = ['match']


class NodeVisitor(object):
    """A shell for writing things that turn parse trees into something useful

    Subclass this, add methods for each expr you care about, instantiate, and
    call ``visit(top_node_of_parse_tree)``. It'll return the useful stuff.

    This API is very similar to that of ``ast.NodeVisitor``.

    We never transform the parse tree in place, because...

    * There are likely multiple references to the same ``Node`` object in a
      parse tree, and changes to one reference would surprise you elsewhere.
    * It makes it impossible to report errors: you'd end up with the "error"
      arrow pointing someplace in a half-transformed mishmash of nodes--and
      that's assuming you're even transforming the tree into another tree.
      Heaven forbid you're making it into a string or something else.

    """
    def visit(self, node):
        method = getattr(self, 'visit_' + node.expr_name, self.generic_visit)

        # Call that method, and show where in the tree it failed if it blows
        # up.
        try:
            return method(node)
        except VisitationException:
            # Don't catch and re-wrap already-wrapped exceptions.
            raise
        except Exception, e:
            # Catch any exception, and tack on a parse tree so it's easier to
            # see where it went wrong.
            exc_class, exc, tb = sys.exc_info()
            visitation_exception = VisitationException(exc, exc_class, node)
            raise visitation_exception.__class__, visitation_exception, tb

    def generic_visit(self, node):
        """Default visitor method"""
        # TODO: Figure out what, if anything, this should do. Some people will
        # want strings; others, other things.
        raise NotImplementedError
