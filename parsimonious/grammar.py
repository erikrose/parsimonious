"""A convenience which constructs expression trees from an easy-to-read
EBNF-like syntax

Use this unless you have a compelling reason not to; it performs some
optimizations that would be tedious to do when constructing an expression tree
by hand.

"""
import ast

from parsimonious.exceptions import UndefinedLabel
from parsimonious.expressions import *
from parsimonious.nodes import NodeVisitor


__all__ = ['Grammar']


class Grammar(dict):
    """A collection of expressions that describe a language

    You can start parsing from the default expression by calling ``parse()``
    directly on the ``Grammar`` object::

        g = Grammar('''
                    polite_greeting = greeting ", my good " title
                    greeting        = "Hi" / "Hello"
                    title           = "madam" / "sir"
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
      increase cache hit ratio. [Is this implemented yet?]

    """
    def __init__(self, dsl, default_rule=None):
        """Construct a grammar.

        :arg default_rule: The name of the rule invoked when you call
            ``parse()`` on the grammar. Defaults to the first rule.

        """
        # Maybe we should keep the original DSL text around in case people want
        # to extend already-compiled grammars. We can't rely on callers to
        # nicely expose their DSL strings. We can either have extending callers
        # pull the text off Grammar.dsl, or we could get fancy and define
        # __add__ on Grammars and strings. Or maybe, if you want to extend a
        # grammar, just prepend (or append?) your string to its, and yours will
        # take precedence. Or use the OMeta delegation syntax. Or yield back
        # the dynamic reconstruction of the DSL.
        rules, first = self._rules_from_dsl(dsl)

        self.update(rules)
        self.default_rule = rules[default_rule] if default_rule else first

    def _rules_from_dsl(self, dsl):
        """Return a 2-tuple: a dict of rule names pointing to their
        expressions, and then the first rule.

        It's a web of expressions, all referencing each other. Typically,
        there's a single root to the web of references, and that root is the
        starting symbol for parsing, but there's nothing saying you can't have
        multiple roots.

        """
        tree = dsl_grammar.parse(dsl)
        return DslVisitor().visit(tree)

    def parse(self, text):
        """Parse some text with the default rule."""
        return self.default_rule.parse(text)


class BootstrappingGrammar(Grammar):
    """The grammar used to recognize the DSL that describes other grammars

    This grammar gets its start from some hard-coded Expressions and claws its
    way from there to an expression tree that describes how to parse the
    grammar description DSL.

    """
    def _rules_from_dsl(self, dsl):
        """Return the rules for parsing the grammar DSL.

        Return a 2-tuple: a dict of rule names pointing to their
        expressions, and then the first rule.

        """
        # Hard-code enough of the rules to parse the grammar that describes the
        # grammar description language, to bootstrap:
        ws = Regex(r'\s+', name='ws')
        _ = Regex(r'[ \t]+', name='_')
        label = Regex(r'[a-zA-Z_][a-zA-Z_0-9]*', name='label')
        quantifier = Regex(r'[*+?]', name='quantifier')
        # This pattern supports empty literals. TODO: A problem?
        literal = Regex(r'u?r?"[^"\\]*(?:\\.[^"\\]*)*"', ignore_case=True, dot_all=True, name='literal')
        regex = Sequence(Literal('~'), literal, Regex('[ilmsux]*', ignore_case=True), name='regex')
        atom = OneOf(label, literal, regex, name='atom')
        quantified = Sequence(atom, quantifier, name='quantified')
        term = OneOf(quantified, atom, name='term')
        another_term = Sequence(_, term, name='another_term')
        sequence = Sequence(term, OneOrMore(another_term), name='sequence')
        or_term = Sequence(_, Literal('/'), another_term, name='or_term')
        or_terms = OneOrMore(or_term, name='or_terms')
        ored = Sequence(term, or_terms, name='ored')
        and_term = Sequence(_, Literal('&'), another_term, name='and_term')
        and_terms = OneOrMore(and_term, name='and_terms')
        anded = Sequence(term, and_terms, name='anded')
        poly_term = OneOf(anded, ored, sequence, name='poly_term')
        rhs = OneOf(poly_term, term, name='rhs')
        eol = Regex(r'[\r\n$]', name='eol')  # TODO: Support $.
        rule = Sequence(Optional(ws), label, Optional(_), Literal('='),
                        Optional(_), rhs, Optional(_), eol, name='rule')
        rules = Sequence(OneOrMore(rule), Optional(ws), name='rules')

        # Use those hard-coded rules to parse the (possibly more extensive) DSL
        # grammar definition. (For example, unless I start using parentheses in
        # the DSL definition itself, I should never have to hard-code
        # expressions for those above.)
        dsl_tree = rules.parse(dsl)

        # Turn the parse tree into a map of expressions:
        return DslVisitor().visit(dsl_tree)


# The grammar for parsing PEG grammar definitions:
# TODO: Support Not. Figure out how tightly it should bind.
# TODO: Support comments.
# This is a nice, simple grammar. We may someday add parentheses or support for
# multi-line rules, but it's a safe bet that the future will always be a
# superset of this.
dsl_text = (r'''
    rules = rule+ ws?
    rule = ws? label _? "=" _? rhs _? eol
    literal = ~"u?r?\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\""is
    eol = ~r"(?:[\r\n]|$)"
    rhs = poly_term / term
    poly_term = anded / ored / sequence
    anded = term and_terms
    and_term = _ "&" another_term
    and_terms = and_term+
    ored = term or_terms
    or_term = _ "/" another_term
    or_terms = or_term+
    sequence = term another_term+
    another_term = _ term
    not_term = "!" term'''  # TODO: Half thought out. Make this work.
    r'''
    term = quantified / atom
    quantified = atom quantifier
    atom = label / literal / regex
    regex = "~" literal ~"[ilmsux]*"i

    quantifier = ~"[*+?]"
    label = ~"[a-zA-Z_][a-zA-Z_0-9]*"
    _ = ~r"[ \t]+"'''  # horizontal whitespace
    r'''
    ws = ~r"\s+"
    ''')


class LazyReference(unicode):
    """A lazy reference to a rule, which we resolve after grokking all the rules"""


class DslVisitor(NodeVisitor):
    """Turns a parse tree of a grammar definition into a map of ``Expression``
    objects

    This is the magic piece that breathes life into a parsed bunch of parse
    rules, allowing them to go forth and parse other things.

    """
    quantifier_classes = {'?': Optional, '*': ZeroOrMore, '+': OneOrMore}

    def visit_quantified(self, quantified, (atom, quantifier)):
        return self.quantifier_classes[quantifier.text](atom)

    def visit_rule(self, rule, (ws, label, _2, equals, _3, rhs, _4, eol)):
        """Assign a name to the Expression and return it."""
        label = unicode(label)  # Turn lazy reference back into text.  # TODO: Remove backtracking.
        rhs.name = label  # Assign a name to the expr.
        return rhs

    def visit_rhs(self, rhs, (term_or_poly,)):
        """Lift the ``term`` or ``poly_term`` up to replace this node."""
        return term_or_poly

    def visit_sequence(self, sequence, (term, one_or_more_other_terms)):  # TODO: right? I'm tired right now. How do the children get passed in? [I think this is right.]
        """A parsed Sequence looks like [term node, OneOrMore node of
        ``another_term``s]. Flatten it out."""
        return Sequence(term, *one_or_more_other_terms)

    def visit_ored(self, ored, (first_term, other_terms)):
        return OneOf(first_term, *other_terms)

    def visit_or_term(self, or_term, (_, slash, term)):
        """Return just the term from an ``or_term``.

        We already know it's going to be ored, from the containing ``ored``.

        """
        return term

    def visit_or_terms(self, or_terms, or_term_children):
        """Raise the list of children up to replace the OneOrMore node around them."""
        return or_term_children

    def visit_anded(self, anded, (first_term, other_terms)):
        return AllOf(first_term, *other_terms)

    def visit_and_term(self, and_term, (_, ampersand, term)):
        """Return just the term from an ``and_term``.

        We already know it's going to be anded, from the containing ``anded``.

        """
        return term

    def visit_and_terms(self, and_terms, and_term_children):
        """Raise the list of children up to replace the OneOrMore node around them."""
        return and_term_children

    def visit_another_term(self, another_term, (_, term)):
        """Strip off the space, and just return the actual term involved in ``another_term``.

        This lets us avoid repeating the stripping of the leading space in
        ``visit_or_term``, ``visit_and_term``, and elsewhere.

        """
        return term

    def visit_poly_term(self, poly_term, (anded_ored_or_sequence,)):
        """Lift up the only child of a ``poly_term`` to take its place."""
        return anded_ored_or_sequence

    def visit_label(self, label, visited_children):
        """Stick a :class:`LazyReference` in the tree as a placeholder.

        We resolve them all later according to the names in the `rules` hash.

        """
        return LazyReference(label.text)

    def visit_term(self, term, (quantified_or_atom,)):
        """``term `` has only 1 child. Lift it up in place of the term."""
        return quantified_or_atom

    def visit_atom(self, atom, (child,)):
        """Lift up the single child to replace this node."""
        return child

    def visit_regex(self, regex, (tilde, literal, flags)):
        """Return a ``Regex`` expression."""
        flags = flags.text.upper()
        pattern = literal.literal  # Pull the string back out of the Literal
                                   # object.
        return Regex(pattern, ignore_case='I' in flags,
                              locale='L' in flags,
                              multiline='M' in flags,
                              dot_all='S' in flags,
                              unicode='U' in flags,
                              verbose='X' in flags)

    def visit_literal(self, literal, visited_children):
        """Turn a string literal into a ``Literal`` that recognizes it."""
        # Piggyback on Python's string support so we can have backslash
        # escaping and niceties like \n, \t, etc.
        # string.decode('string_escape') would have been a lower-level
        # possibility.
        return Literal(ast.literal_eval(literal.text))

    def generic_visit(self, node, visited_children):
        """Replace childbearing nodes with a list of their children; keep
        others untouched.

        For our case, if a node has children, only the children are important.
        Otherwise, keep the node around for (for example) the flags of the
        regex rule. Most of these kept-around nodes are subsequently thrown
        away by the other visitor methods.

        We can't simple hang the visited children off the original node; that
        would be disastrous if the node occurred in more than one place in the
        tree.

        """
        return visited_children or node  # should semantically be a tuple

    def visit_rules(self, node, (rules, ws)):
        """Collate all the rules into a map. Return (map, default rule).

        The default rule is the first one. Or, if you have more than one rule
        of that name, it's the last-occurring rule of that name. (This lets you
        override the default rule when you extend a grammar.)

        """
        # TODO: Too big. Break up.
        rule_map = {}

        def resolve_refs(expr):
            """Turn references into the things they actually reference.

            Walk the expression tree, looking for _LazyReferences. When we find
            one, replace it with rules[the reference].

            """
            if isinstance(expr, LazyReference):
                try:
                    return rule_map[expr]
                except KeyError:
                    raise UndefinedLabel(expr)
            else:
                members = getattr(expr, 'members', None)
                if members:
                    expr.members = [resolve_refs(m) for m in members]
                return expr

        # Map each rule's name to its Expression. Later rules of the same name
        # override earlier ones. This lets us define rules multiple times and
        # have the last declarations win, so you can extend grammars by
        # concatenation.
        rule_map = dict((expr.name, expr) for expr in rules)

        # Resolve references. This takes care of cycles and plain old forward
        # references.
        for k, v in rule_map.iteritems():
            rule_map[k] = resolve_refs(v)

        return rule_map, rules[0]


# Bootstrap to level 1...
dsl_grammar = BootstrappingGrammar(dsl_text)
# ...and then to level 2. This establishes that the node tree of our grammar
# DSL is built by the same machinery that will build that of our users'
# grammars. And the correctness of that tree is tested, indirectly, in
# test_grammar.
dsl_grammar = Grammar(dsl_text)

# TODO: Teach Expression trees how to spit out Python representations of
# themselves. Then we can just paste that in about, and we won't have to
# bootstrap on import. Though it'll be a little less DRY.
