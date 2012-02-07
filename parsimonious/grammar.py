"""A convenience which constructs expression trees from an easy-to-read EBNF-like syntax

Use this unless you have a compelling reason not to; it performs some
optimizations that would be tedious to do when constructing an expression tree
by hand.

"""
import ast

from parsimonious.exceptions import UndefinedLabel
from parsimonious.expressions import *
from parsimonious.nodes import NodeVisitor


class Grammar(dict):
    """A collection of expressions that describe a language

    You can start parsing from the default expression by calling ``parse()``
    directly on the ``Grammar`` object::

        g = Grammar('''
                    polite_greeting = greeting ", my good sir"
                    greeting        = Hi / Hello
                    ''')
        g.parse('Hello, my good sir')

    Or start parsing from any of the other expressions; you can pull them out
    of the grammar as if it were a dictionary::

        g['greeting'].parse('Hi')

    You could also just construct a bunch of ``Expression`` objects yourself
    and stitch them together into a language, but using a ``Grammar`` has some
    important advantages:

    * Languages are much easier to define in the nice syntax it provides.
    * Circular references aren't a pain.
    * It does all kinds of whizzy space- and time-saving optimizations, like
      factoring up repeated subexpressions into a single object, which should
      increase cache hit ratio.

    """
    def __init__(self, peg, default_rule=None):
        """Construct a grammar

        :arg default_rule: The name of the rule invoked when you call
            ``parse()`` on the grammar. Defaults to the first rule.

        """
        # Maybe we should keep the original PEG text around in case people want
        # to extend already-compiled grammars. We can't rely on callers to
        # nicely expose their PEG strings. We can either have extending callers
        # pull the text off Grammar.peg, or we could get fancy and define
        # __add__ on Grammars and strings. Or maybe, if you want to extend a
        # grammar, just prepend (or append?) your string to its, and yours will
        # take precedence.
        #
        # Can we deduce what the starting symbol is, if there is one? If not,
        # it would be nice to be able to pass it in so we could just call
        # g.parse('whatever') and get a reasonable behavior most of the time.
        rules, first = self._rules_from_peg(peg)
        self.update(rules)
        self.default_rule = rules[default_rule] if default_rule else first

    def _rules_from_peg(self, peg):
        """Return a dict of rule names pointing to their expressions.

        It's a web of expressions, all referencing each other. Typically,
        there's a single root to the web of references, and that root is the
        starting symbol for parsing, but there's nothing saying you can't have
        multiple roots.

        """
        # TODO: Unstub.
        # Hard-code the rules for the DSL, to bootstrap:
        ws = Regex(r'\s+')
        _ = Regex(r'[ \t]+')
        label = Regex(r'[a-zA-Z_][a-zA-Z_0-9]*')
        quantifier = Regex(r'[*+?]')
        # This pattern supports empty literals. TODO: A problem?
        literal = Regex(r'u?r?"[^"\\]*(?:\\.[^"\\]*)*"', ignore_case=True, dot_all=True)
        regex = Sequence(Literal('~'), literal, Regex('[ilmsux]*', ignore_case=True))
        atom = OneOf(label, literal, regex)
        quantified = Sequence(atom, quantifier)
        term = OneOf(quantified, atom)
        another_term = Sequence(_, term)
        sequence = Sequence(term, OneOrMore(another_term))
        or_term = Sequence(_, Literal('/'), another_term)
        ored = Sequence(term, OneOrMore(or_term))
        and_term = Sequence(_, Literal('&'), another_term)
        anded = Sequence(term, OneOrMore(and_term))
        poly_term = OneOf(anded, ored, sequence)
        rhs = OneOf(poly_term, term)
        eol = Regex(r'[\r\n$]')  # TODO: Support $.
        rule = Sequence(Optional(ws), label, Optional(_), Literal('='),
                        Optional(_), rhs, Optional(_), eol)
        rules = Sequence(OneOrMore(rule), Optional(ws))

        peg_rules = {}
        for k, v in ((x, y) for (x, y) in locals().iteritems() if isinstance(y, Expression)):
            v.name = k
            peg_rules[k] = v
        return peg_rules, rules

    def parse(self, text):
        """Parse some text with the default rule."""
        return self.default_rule.parse(text)


# The grammar for parsing PEG grammar definitions:
# TODO: Support Not. Figure out how tightly it should bind.
# This is a nice, simple grammar. We may someday add parentheses or support for
# multi-line rules, but it's a safe bet that the future will always be a
# superset of this.
peg_grammar = Grammar('''
    rules = rule+ ws?
    rule = ws? label _? "=" _? rhs _? eol
    eol = ~r"[\r\n]"  # TODO: $
    rhs = poly_term / term
    poly_term = anded / ored / sequence
    anded = term and_term+
    and_term = _ "&" another_term
    ored = term or_term+
    or_term = _ "/" another_term
    sequence = term another_term+
    another_term = _ term
    not_term = "!" term  # TODO: Half thought out. Make this work.
    term = quantified / atom
    quantified = atom quantifier
    atom = label / literal / regex
    regex = "~" literal ~"[ilmsux]*"i
    literal = ~"u?r?\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\""is
    quantifier = ~"[*+?]"
    label = ~"[a-zA-Z_][a-zA-Z_0-9]*"
    _ = ~r"[ \t]+"  # horizontal whitespace
    ws = ~r"\s+"
    ''')


class _LazyReference(unicode):
    """A lazy reference to a rule, which we resolve after grokking all the rules"""


class PegVisitor(NodeVisitor):
    """Turns a parse tree of a grammar definition into a map of ``Expression`` objects"""

    def visit_rule(self, node):
        """Assign a name to the Expression and return it."""
        _, label, _, equals, _, rhs, _, eol = node.children
        rhs = self.visit(rhs)
        label = unicode(self.visit(label))  # Turn into text.
        rhs.name = label  # Assign a name to the expr.
        return rhs

    def visit_rhs(self, node):
        """Lift the ``term`` or ``poly_term`` up to replace this node."""
        term_or_poly, = node.children
        return self.visit(term_or_poly)

    def visit_label(self, node):
        """Stick a :class:`_LazyReference` in the tree as a placeholder.

        We resolve them all later according to the names in the `rules` hash.

        """
        return _LazyReference(node.text)

    def visit_term(self, node):
        """``term `` has only 1 child. Lift it up in place of the term."""
        quantified_or_atom, = node.children
        return self.visit(quantified_or_atom)  # TODO: Factor up.

    def visit_atom(self, node):
        """Lift up the single child to replace this node."""
        return self.visit(node.children[0])

    def visit_regex(self, node):
        """Return a ``Regex`` expression."""
        tilde, pattern, flags = node.children
        pattern = self.visit(pattern)  # Turn pattern literal into a string.
        flags = flags.text.upper()
        return Regex(pattern, ignore_case='I' in flags,
                              locale='L' in flags,
                              multiline='M' in flags,
                              dot_all='S' in flags,
                              unicode='U' in flags,
                              verbose='X' in flags)

    def visit_literal(self, node):
        """Turn a literal into the text it represents."""
        # Piggyback on Python's string support so we can have backslash
        # escaping and niceties like \n, \t, etc.
        # string.decode('string_escape') would have been a lower-level
        # possibility.
        return ast.literal_eval(node.text)

    def visit_rules(self, node):
        """Collate all the rules into a map. Return (map, default rule).

        The default rule is the first one. Or, if you have more than one rule
        of that name, it's the last-occurring rule of that name. (This lets you
        override the default rule when you extend a grammar.)

        """
        # TODO: Too big. Break up.
        rules, ws = node.children
        rule_map = {}

        def resolve_refs(expr):
            """Turn references into the things they actually reference.

            Walk the expression tree, looking for _LazyReferences. When we find
            one, replace it with rules[the reference].

            """
            if isinstance(expr, _LazyReference):
                try:
                    return rule_map[expr]
                except KeyError:
                    raise UndefinedLabel(expr)
            else:
                members = getattr(expr, 'members', None)
                if members:
                    expr.members = [resolve_refs(m) for m in members]
                return expr

        # Turn each rule into an Expression. Later rules of the same name
        # override earlier ones.
        first = None
        for n in rules.children:
            expr = self.visit(n)
            rule_map[expr.name] = expr
            if not first:
                first = expr

        # Resolve references. This lets us define rules multiple times and have
        # the last declarations win, so you can extend grammars by
        # concatenation. It also takes care of cycles and plain old forward
        # references.
        for k, v in rule_map.iteritems():
            rule_map[k] = resolve_refs(v)

        return rule_map, first
