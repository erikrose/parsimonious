"""Nodes that make up parse trees

Parsing spits out a tree of these, which you can then tell to walk itself and
spit out a useful value. Or you can walk it yourself; the structural attributes
are public.

"""
# TODO: If this is slow, think about using cElementTree or something.
import sys

from parsimonious.exceptions import VisitationError
from parsimonious.utils import StrAndRepr


class Node(StrAndRepr):
    """A parse tree node

    Consider these immutable once constructed. As a side effect of a
    memory-saving strategy in the cache, multiple references to a single
    ``Node`` might be returned in a single parse tree. So, if you start
    messing with one, you'll see surprising parallel changes pop up elsewhere.

    My philosophy is that parse trees (and their nodes) should be
    representation-agnostic. That is, they shouldn't get all mixed up with what
    the final rendered form of a wiki page (or the intermediate representation
    of a programming language, or whatever) is going to be: you should be able
    to parse once and render several representations from the tree, one after
    another.

    """
    # I tried making this subclass list, but it got ugly. I had to construct
    # invalid ones and patch them up later, and there were other problems.
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

    def __iter__(self):
        """Support looping over my children and doing tuple unpacks on me.

        It can be very handy to unpack nodes in arg lists; see
        :class:`PegVisitor` for an example.

        """
        return iter(self.children)

    @property
    def text(self):
        """Return the text this node matched."""
        return self.full_text[self.start:self.end]

    # From here down is just stuff for testing and debugging.

    def prettily(self, error=None):
        """Return a unicode, pretty-printed representation of me.

        :arg error: The node to highlight because an error occurred there

        """
        # TODO: If a Node appears multiple times in the tree, we'll point to
        # them all. Whoops.
        def indent(text):
            return '\n'.join(('    ' + line) for line in text.splitlines())
        ret = [u'<%s%s matching "%s">%s' % (
            self.__class__.__name__,
            (' called "%s"' % self.expr_name) if self.expr_name else '',
            self.text,
            '  <-- *** We were here. ***' if error is self else '')]
        for n in self:
            ret.append(indent(n.prettily(error=error)))
        return '\n'.join(ret)

    def __unicode__(self):
        """Return a compact, human-readable representation of me."""
        return self.prettily()

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

    def __repr__(self, top_level=True):
        """Return a bit of code (though not an expression) that will recreate
        me."""
        # repr() of unicode flattens everything out to ASCII, so we don't need
        # to explicitly encode things afterward.
        ret = ["s = %r" % self.full_text] if top_level else []
        ret.append("%s(%r, s, %s, %s%s)" % (
            self.__class__.__name__,
            self.expr_name,
            self.start,
            self.end,
            (', children=[%s]' %
             ', '.join([c.__repr__(top_level=False) for c in self.children]))
            if self.children else ''))
        return '\n'.join(ret)


class RegexNode(Node):
    """Node returned from a ``Regex`` expression

    Grants access to the ``re.Match`` object, in case you want to access
    capturing groups, etc.

    """
    __slots__ = ['match']


class NodeVisitor(object):
    """A shell for writing things that turn parse trees into something useful

    Performs a depth-first traversal of an AST. Subclass this, add methods for
    each expr you care about, instantiate, and call
    ``visit(top_node_of_parse_tree)``. It'll return the useful stuff.

    This API is very similar to that of ``ast.NodeVisitor``.

    We never transform the parse tree in place, because...

    * There are likely multiple references to the same ``Node`` object in a
      parse tree, and changes to one reference would surprise you elsewhere.
    * It makes it impossible to report errors: you'd end up with the "error"
      arrow pointing someplace in a half-transformed mishmash of nodes--and
      that's assuming you're even transforming the tree into another tree.
      Heaven forbid you're making it into a string or something else.

    """
    # These could easily all be static methods, but that adds at least as much
    # user-facing weirdness as the ``()`` chars for instantiation. And this
    # way, we're forward compatible if we or the user ever wants to add any
    # state: options, for instance, or a symbol table constructed from a
    # programming language's AST.

    # TODO: If we need to optimize this, we can go back to putting subclasses
    # in charge of visiting children; they know when not to bother. Or we can
    # mark nodes as not descent-worthy in the grammar.
    def visit(self, node):
        method = getattr(self, 'visit_' + node.expr_name, self.generic_visit)

        # Call that method, and show where in the tree it failed if it blows
        # up.
        try:
            return method(node, [self.visit(n) for n in node])
        except VisitationError:
            # Don't catch and re-wrap already-wrapped exceptions.
            raise
        except Exception as e:
            # Catch any exception, and tack on a parse tree so it's easier to
            # see where it went wrong.
            exc_class, exc, tb = sys.exc_info()
            raise VisitationError, (exc, exc_class, node), tb

    def generic_visit(self, node, visited_children):
        """Default visitor method

        :arg node: The node we're visiting
        :arg visited_children: The results of visiting the children of that
            node, in a list

        I'm not sure there's an implementation of this that makes sense across
        all (or even most) use cases, so we leave it to subclasses to implement
        for now.

        """
        raise NotImplementedError

    # Convenience methods you can call from your own visitors:

    def lift_child(self, node, (first_child,)):
        """Lift the sole child of ``node`` up to replace the node."""
        return first_child
