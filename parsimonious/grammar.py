"""A convenience which constructs expression trees from an easy-to-read syntax

Use this unless you have a compelling reason not to; it performs some
optimizations that would be tedious to do when constructing an expression tree
by hand.

"""
import ast

from parsimonious.exceptions import BadGrammar, UndefinedLabel
from parsimonious.expressions import (Literal, Regex, Sequence, OneOf,
    Lookahead, Optional, ZeroOrMore, OneOrMore, Not)
from parsimonious.nodes import NodeVisitor
from parsimonious.utils import StrAndRepr


__all__ = ['Grammar']


class Grammar(StrAndRepr, dict):
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
    def __init__(self, rules, default_rule=None):
        """Construct a grammar.

        :arg rules: A string of production rules, one per line. There must be
            at least one rule.
        :arg default_rule: The name of the rule invoked when you call
            ``parse()`` on the grammar. Defaults to the first rule.

        """
        # We can either have extending callers pull the rule text out of repr,
        # or we could get fancy and define __add__ on Grammars and strings. Or
        # maybe, if you want to extend a grammar, just prepend (or append?)
        # your string to its, and yours will take precedence. Or use the OMeta
        # delegation syntax.
        exprs, first = self._expressions_from_rules(rules)

        self.update(exprs)
        self.default_rule = exprs[default_rule] if default_rule else first

    def _expressions_from_rules(self, rules):
        """Return a 2-tuple: a dict of rule names pointing to their
        expressions, and then the first rule.

        It's a web of expressions, all referencing each other. Typically,
        there's a single root to the web of references, and that root is the
        starting symbol for parsing, but there's nothing saying you can't have
        multiple roots.

        """
        tree = rule_grammar.parse(rules)
        if tree is None:
            raise BadGrammar('There is an error in your grammar definition. '
                             'Sorry for the vague error reporting at the '
                             'moment.')

        return RuleVisitor().visit(tree)

    def parse(self, text):
        """Parse some text with the default rule."""
        return self.default_rule.parse(text)

    def match(self, text, pos=0):
        """Parse some text with the default rule but not necessarily all the
        way to the end.

        :arg pos: The index at which to start parsing

        """
        return self.default_rule.match(text, pos=pos)

    def __unicode__(self):
        """Return a rule string that, when passed to the constructor, would
        reconstitute the grammar."""
        exprs = [self.default_rule]
        exprs.extend(expr for expr in self.itervalues() if
                     expr is not self.default_rule)
        return '\n'.join(expr.as_rule() for expr in exprs)

    def __repr__(self):
        """Return an expression that will reconstitute the grammar."""
        return "Grammar('%s')" % str(self).encode('string_escape')


class BootstrappingGrammar(Grammar):
    """The grammar used to recognize the textual rules that describe other
    grammars

    This grammar gets its start from some hard-coded Expressions and claws its
    way from there to an expression tree that describes how to parse the
    grammar description syntax.

    """
    def _expressions_from_rules(self, rule_syntax):
        """Return the rules for parsing the grammar definition syntax.

        Return a 2-tuple: a dict of rule names pointing to their expressions,
        and then the top-level expression for the first rule.

        """
        # Hard-code enough of the rules to parse the grammar that describes the
        # grammar description language, to bootstrap:
        ws = Regex(r'\s+', name='ws')
        comment = Regex(r'#[^\r\n]*', name='comment')
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
        ored = Sequence(term, OneOrMore(or_term), name='ored')
        expression = OneOf(ored, sequence, term, name='expression')
        eol = Regex(r'[\r\n$]', name='eol')  # TODO: Support $.
        rule = Sequence(label, Optional(_), Literal('='), Optional(_),
                        expression, Optional(_), Optional(comment), eol,
                        name='rule')
        rule_or_rubbish = OneOf(rule, ws, comment, name='rule_or_rubbish')
        rules = OneOrMore(rule_or_rubbish, name='rules')

        # Use those hard-coded rules to parse the (more extensive) rule syntax.
        # (For example, unless I start using parentheses in the rule language
        # definition itself, I should never have to hard-code expressions for
        # those above.)
        rule_tree = rules.parse(rule_syntax)

        # Turn the parse tree into a map of expressions:
        return RuleVisitor().visit(rule_tree)


# The grammar for parsing PEG grammar definitions:
# This is a nice, simple grammar. We may someday add support for multi-line
# rules or other sugar, but it's a safe bet that the future will always be a
# superset of this.
rule_syntax = (r'''
    rules = rule_or_rubbish+
    rule_or_rubbish = rule / ws / comment
    rule = label _? "=" _? expression _? comment? eol
    literal = ~"u?r?\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\""is
    eol = ~r"(?:[\r\n]|$)"
    expression = ored / sequence / term
    or_term = _ "/" another_term
    ored = term or_term+
    sequence = term another_term+
    another_term = _ term
    not_term = "!" term
    lookahead_term = "&" term
    term = not_term / lookahead_term / quantified / atom
    quantified = atom quantifier
    atom = label / literal / regex / parenthesized
    regex = "~" literal ~"[ilmsux]*"i
    parenthesized = "(" expression ")"
    quantifier = ~"[*+?]"
    label = ~"[a-zA-Z_][a-zA-Z_0-9]*"
    _ = ~r"[ \t]+"  # horizontal whitespace
    ws = ~r"\s+"
    comment = ~r"#[^\r\n]*"
    ''')


class LazyReference(unicode):
    """A lazy reference to a rule, which we resolve after grokking all the
    rules"""


class RuleVisitor(NodeVisitor):
    """Turns a parse tree of a grammar definition into a map of ``Expression``
    objects

    This is the magic piece that breathes life into a parsed bunch of parse
    rules, allowing them to go forth and parse other things.

    """
    quantifier_classes = {'?': Optional, '*': ZeroOrMore, '+': OneOrMore}

    visit_rule_or_rubbish = visit_expression = visit_term = visit_atom = \
        NodeVisitor.lift_child

    def visit_parenthesized(self, parenthesized, (left_paren, expression,
                                                  right_paren)):
        """Treat a parenthesized subexpression as just its contents.

        Its position in the tree suffices to maintain its grouping semantics.

        """
        return expression

    def visit_quantified(self, quantified, (atom, quantifier)):
        return self.quantifier_classes[quantifier.text](atom)

    def visit_lookahead_term(self, lookahead_term, (ampersand, term)):
        return Lookahead(term)

    def visit_not_term(self, not_term, (exclamation, term)):
        return Not(term)

    def visit_ws(self, ws, visited_children):
        """Stomp out ``ws`` nodes so visit_rules can easily filter them out."""

    def visit_comment(self, comment, visited_children):
        """Stomp out ``comment`` nodes so visit_rules can easily filter them
        out."""

    def visit_rule(self, rule, (label, _2, equals, _3, expression, _4, comment,
                                eol)):
        """Assign a name to the Expression and return it."""
        label = unicode(label)  # Turn lazy reference back into text.  # TODO: Remove backtracking.
        expression.name = label  # Assign a name to the expr.
        return expression

    def visit_sequence(self, sequence, (term, other_terms)):
        """A parsed Sequence looks like [term node, OneOrMore node of
        ``another_term``s]. Flatten it out."""
        return Sequence(term, *other_terms)

    def visit_ored(self, ored, (first_term, other_terms)):
        return OneOf(first_term, *other_terms)

    def visit_or_term(self, or_term, (_, slash, term)):
        """Return just the term from an ``or_term``.

        We already know it's going to be ored, from the containing ``ored``.

        """
        return term

    def visit_another_term(self, another_term, (_, term)):
        """Strip off the space, and just return the actual term involved in
        ``another_term``.

        This lets us avoid repeating the stripping of the leading space in
        ``visit_or_term``, ``visit_and_term``, and elsewhere.

        """
        return term

    def visit_label(self, label, visited_children):
        """Stick a :class:`LazyReference` in the tree as a placeholder.

        We resolve them all later according to the names in the `rules` hash.

        """
        return LazyReference(label.text)

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

        We can't simply hang the visited children off the original node; that
        would be disastrous if the node occurred in more than one place in the
        tree.

        """
        return visited_children or node  # should semantically be a tuple

    def visit_rules(self, node, rule_or_rubbishes):
        """Collate all the rules into a map. Return (map, default rule).

        The default rule is the first one. Or, if you have more than one rule
        of that name, it's the last-occurring rule of that name. (This lets you
        override the default rule when you extend a grammar.)

        """
        rule_map = {}

        # Drop the ws and comments:
        rules = [r for r in rule_or_rubbishes if r is not None]

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
rule_grammar = BootstrappingGrammar(rule_syntax)
# ...and then to level 2. This establishes that the node tree of our rule
# syntax is built by the same machinery that will build trees of our users'
# grammars. And the correctness of that tree is tested, indirectly, in
# test_grammar.
rule_grammar = Grammar(rule_syntax)

# TODO: Teach Expression trees how to spit out Python representations of
# themselves. Then we can just paste that in above, and we won't have to
# bootstrap on import. Though it'll be a little less DRY. [Ah, but this is not
# so clean, because it would have to output multiple statements to get multiple
# refs to a single expression hooked up.]
