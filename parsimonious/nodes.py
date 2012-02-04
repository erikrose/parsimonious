"""Nodes that make up parse trees

Parsing spits out a tree of these, which you can then tell to walk itself and
spit out a useful value. Or you can walk it yourself; the structural attributes
are public.

"""
# TODO: If this is slow, think about using cElementTree or something.

class Node(object):
    """A parse tree node

    My philosophy is that parse trees (and their nodes) should be
    representation-agnostic. That is, they shouldn't get all mixed up in what
    the final rendered form of a wiki page (or the intermediate representation
    of a programming language) is going to be: you should be able to parse once
    and render several representations from the tree, one after another.

    """
    __slots__ = ['rule_name',  # The name of the rule that generated me
                 'start', # The position in the text where that rule started matching
                 'end',   # The position after start where the rule first didn't
                          # match. [start:end] follow Python slice conventions.
                 'children',  # List of child parse tree nodes
                 'text']  # The full text fed to the parser

    def __init__(self, rule_name, text, start, end, children=None):
        self.rule_name = rule_name
        self.text = text
        self.start = start
        self.end = end
        self.children = children or []

    def __unicode__(self):
        return u'<%s "%s">' % (self.rule_name,
                               self.text[self.start:self.end])
        # TODO: Hang children off the bottom, indented, recursively, like a TreeView.

    __str__ = __repr__ = __unicode__


class NodeVisitor(object):
    """A shell for writing things that turn parse trees into something useful

    Subclass this, add methods for each rule you care about, instantiate, and
    call ``visit(top_node_of_parse_tree)``. It'll return the useful stuff.

    This API is very similar to that of ``ast.NodeVisitor``.

    """
    def visit(self, node):
        method = getattr(self, 'visit_' + node.rule_name, self.generic_visit)
        return method(node)

    def generic_visit(self):
        """Default visitor method"""
        # TODO: Figure out what, if anything, this should do. Some people will
        # want strings; others, other things.
        raise NotImplementedError
