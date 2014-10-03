"""A convenience which constructs expression trees from an easy-to-read syntax

Use this unless you have a compelling reason not to; it performs some
optimizations that would be tedious to do when constructing an expression tree
by hand.

"""
import ast
from inspect import isfunction, ismethod

from parsimonious.exceptions import UndefinedLabel
from parsimonious.expressions import (Literal, Regex, Sequence, OneOf,
    Lookahead, Optional, ZeroOrMore, OneOrMore, Not, expression)
from parsimonious.nodes import NodeVisitor
from parsimonious.utils import StrAndRepr


class Grammar(StrAndRepr, dict):
    """A collection of rules that describe a language

    You can start parsing from the default rule by calling ``parse()``
    directly on the ``Grammar`` object::

        g = Grammar('''
                    polite_greeting = greeting ", my good " title
                    greeting        = "Hi" / "Hello"
                    title           = "madam" / "sir"
                    ''')
        g.parse('Hello, my good sir')

    Or start parsing from any of the other rules; you can pull them out of the
    grammar as if it were a dictionary::

        g['title'].parse('sir')

    You could also just construct a bunch of ``Expression`` objects yourself
    and stitch them together into a language, but using a ``Grammar`` has some
    important advantages:

    * Languages are much easier to define in the nice syntax it provides.
    * Circular references aren't a pain.
    * It does all kinds of whizzy space- and time-saving optimizations, like
      factoring up repeated subexpressions into a single object, which should
      increase cache hit ratio. [Is this implemented yet?]

    """
    def __init__(self, rules='', **more_rules):
        """Construct a grammar.

        :arg rules: A string of production rules, one per line.
        :arg default_rule: The name of the rule invoked when you call
            :meth:`parse()` or :meth:`match()` on the grammar. Defaults to the
            first rule. Falls back to None if there are no string-based rules
            in this grammar.
        :arg more_rules: Additional kwargs whose names are rule names and
            values are Expressions or custom-coded callables which accomplish
            things the built-in rule syntax cannot. These take precedence over
            ``rules`` in case of naming conflicts.

        """
        decorated_custom_rules = dict(
            (k, expression(v, k, self) if isfunction(v) or
                                          ismethod(v) else
                v) for k, v in more_rules.iteritems())

        exprs, first = self._expressions_from_rules(rules, decorated_custom_rules)

        self.update(exprs)
        self.default_rule = first  # may be None

    def default(self, rule_name):
        """Return a new Grammar whose :term:`default rule` is ``rule_name``."""
        new = self._copy()
        new.default_rule = new[rule_name]
        return new

    def _copy(self):
        """Return a shallow copy of myself.

        Deep is unnecessary, since Expression trees are immutable. Subgrammars
        recreate all the Expressions from scratch, and AbstractGrammars have
        no Expressions.

        """
        new = Grammar(**self)
        new.default_rule = self.default_rule
        return new

    def _expressions_from_rules(self, rules, custom_rules):
        """Return a 2-tuple: a dict of rule names pointing to their
        expressions, and then the first rule.

        It's a web of expressions, all referencing each other. Typically,
        there's a single root to the web of references, and that root is the
        starting symbol for parsing, but there's nothing saying you can't have
        multiple roots.

        :arg custom_rules: A map of rule names to custom-coded rules:
            Expressions

        """
        tree = rule_grammar.parse(rules)
        return RuleVisitor(custom_rules).visit(tree)

    def parse(self, text, pos=0):
        """Parse some text with the :term:`default rule`.

        :arg pos: The index at which to start parsing

        """
        self._check_default_rule()
        return self.default_rule.parse(text, pos=pos)

    def match(self, text, pos=0):
        """Parse some text with the :term:`default rule` but not necessarily
        all the way to the end.

        :arg pos: The index at which to start parsing

        """
        self._check_default_rule()
        return self.default_rule.match(text, pos=pos)

    def _check_default_rule(self):
        """Raise RuntimeError if there is no default rule defined."""
        if not self.default_rule:
            raise RuntimeError("Can't call parse() on a Grammar that has no "
                               "default rule. Choose a specific rule instead, "
                               "like some_grammar['some_rule'].parse(...).")

    def __unicode__(self):
        """Return a rule string that, when passed to the constructor, would
        reconstitute the grammar."""
        exprs = [self.default_rule] if self.default_rule else []
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
    def _expressions_from_rules(self, rule_syntax, custom_rules):
        """Return the rules for parsing the grammar definition syntax.

        Return a 2-tuple: a dict of rule names pointing to their expressions,
        and then the top-level expression for the first rule.

        """
        # Hard-code enough of the rules to parse the grammar that describes the
        # grammar description language, to bootstrap:
        comment = Regex(r'#[^\r\n]*', name='comment')
        meaninglessness = OneOf(Regex(r'\s+'), comment, name='meaninglessness')
        _ = ZeroOrMore(meaninglessness, name='_')
        equals = Sequence(Literal('='), _, name='equals')
        label = Sequence(Regex(r'[a-zA-Z_][a-zA-Z_0-9]*'), _, name='label')
        reference = Sequence(label, Not(equals), name='reference')
        quantifier = Sequence(Regex(r'[*+?]'), _, name='quantifier')
        # This pattern supports empty literals. TODO: A problem?
        spaceless_literal = Regex(r'u?r?"[^"\\]*(?:\\.[^"\\]*)*"',
                                  ignore_case=True,
                                  dot_all=True,
                                  name='spaceless_literal')
        literal = Sequence(spaceless_literal, _, name='literal')
        regex = Sequence(Literal('~'),
                         literal,
                         Regex('[ilmsux]*', ignore_case=True),
                         _,
                         name='regex')
        atom = OneOf(reference, literal, regex, name='atom')
        quantified = Sequence(atom, quantifier, name='quantified')

        term = OneOf(quantified, atom, name='term')
        not_term = Sequence(Literal('!'), term, _, name='not_term')
        term.members = (not_term,) + term.members

        sequence = Sequence(term, OneOrMore(term), name='sequence')
        or_term = Sequence(Literal('/'), _, term, name='or_term')
        ored = Sequence(term, OneOrMore(or_term), name='ored')
        expression = OneOf(ored, sequence, term, name='expression')
        rule = Sequence(label, equals, expression, name='rule')
        rules = Sequence(_, OneOrMore(rule), name='rules')

        # Use those hard-coded rules to parse the (more extensive) rule syntax.
        # (For example, unless I start using parentheses in the rule language
        # definition itself, I should never have to hard-code expressions for
        # those above.)

        rule_tree = rules.parse(rule_syntax)

        # Turn the parse tree into a map of expressions:
        return RuleVisitor().visit(rule_tree)


# The grammar for parsing PEG grammar definitions:
# This is a nice, simple grammar. We may someday add to it, but it's a safe bet
# that the future will always be a superset of this.
rule_syntax = (r'''
    # Ignored things (represented by _) are typically hung off the end of the
    # leafmost kinds of nodes. Literals like "/" count as leaves.

    rules = _ rule*
    rule = label equals expression
    equals = "=" _
    literal = spaceless_literal _

    # So you can't spell a regex like `~"..." ilm`:
    spaceless_literal = ~"u?r?\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\""is /
                        ~"u?r?'[^'\\\\]*(?:\\\\.[^'\\\\]*)*'"is

    expression = ored / sequence / term
    or_term = "/" _ term
    ored = term or_term+
    sequence = term term+
    not_term = "!" term _
    lookahead_term = "&" term _
    term = not_term / lookahead_term / quantified / atom
    quantified = atom quantifier
    atom = reference / literal / regex / parenthesized
    regex = "~" spaceless_literal ~"[ilmsux]*"i _
    parenthesized = "(" _ expression ")" _
    quantifier = ~"[*+?]" _
    reference = label !equals

    # A subsequent equal sign is the only thing that distinguishes a label
    # (which begins a new rule) from a reference (which is just a pointer to a
    # rule defined somewhere else):
    label = ~"[a-zA-Z_][a-zA-Z_0-9]*" _

    # _ = ~r"\s*(?:#[^\r\n]*)?\s*"
    _ = meaninglessness*
    meaninglessness = ~r"\s+" / comment
    comment = ~r"#[^\r\n]*"
    ''')


class LazyReference(unicode):
    """A lazy reference to a rule, which we resolve after grokking all the
    rules"""

    name = u''

    # Just for debugging:
    def _as_rhs(self):
        return u'<LazyReference to %s>' % self


class RuleVisitor(NodeVisitor):
    """Turns a parse tree of a grammar definition into a map of ``Expression``
    objects

    This is the magic piece that breathes life into a parsed bunch of parse
    rules, allowing them to go forth and parse other things.

    """
    quantifier_classes = {'?': Optional, '*': ZeroOrMore, '+': OneOrMore}

    visit_expression = visit_term = visit_atom = NodeVisitor.lift_child

    def __init__(self, custom_rules=None):
        """Construct.

        :arg custom_rules: A dict of {rule name: expression} holding custom
            rules which will take precedence over the others

        """
        self.custom_rules = custom_rules or {}

    def visit_parenthesized(self, parenthesized, (left_paren, _1,
                                                  expression,
                                                  right_paren, _2)):
        """Treat a parenthesized subexpression as just its contents.

        Its position in the tree suffices to maintain its grouping semantics.

        """
        return expression

    def visit_quantifier(self, quantifier, (symbol, _)):
        """Turn a quantifier into just its symbol-matching node."""
        return symbol

    def visit_quantified(self, quantified, (atom, quantifier)):
        return self.quantifier_classes[quantifier.text](atom)

    def visit_lookahead_term(self, lookahead_term, (ampersand, term, _)):
        return Lookahead(term)

    def visit_not_term(self, not_term, (exclamation, term, _)):
        return Not(term)

    def visit_rule(self, rule, (label, equals, expression)):
        """Assign a name to the Expression and return it."""
        expression.name = label  # Assign a name to the expr.
        return expression

    def visit_sequence(self, sequence, (term, other_terms)):
        """A parsed Sequence looks like [term node, OneOrMore node of
        ``another_term``s]. Flatten it out."""
        return Sequence(term, *other_terms)

    def visit_ored(self, ored, (first_term, other_terms)):
        return OneOf(first_term, *other_terms)

    def visit_or_term(self, or_term, (slash, _, term)):
        """Return just the term from an ``or_term``.

        We already know it's going to be ored, from the containing ``ored``.

        """
        return term

    def visit_label(self, label, (name, _)):
        """Turn a label into a unicode string."""
        return name.text

    def visit_reference(self, reference, (label, not_equals)):
        """Stick a :class:`LazyReference` in the tree as a placeholder.

        We resolve them all later.

        """
        return LazyReference(label)

    def visit_regex(self, regex, (tilde, literal, flags, _)):
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

    def visit_spaceless_literal(self, spaceless_literal, visited_children):
        """Turn a string literal into a ``Literal`` that recognizes it."""
        # Piggyback on Python's string support so we can have backslash
        # escaping and niceties like \n, \t, etc.
        # string.decode('string_escape') would have been a lower-level
        # possibility.
        return Literal(ast.literal_eval(spaceless_literal.text))

    def visit_literal(self, literal, (spaceless_literal, _)):
        """Pick just the literal out of a literal-and-junk combo."""
        return spaceless_literal

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

    def _resolve_refs(self, rule_map, expr):
        """Return an expression with all its lazy references recursively
        resolved.

        Resolve any lazy references in the expression ``expr``, recursing into
        all subexpressions.

        """
        if isinstance(expr, LazyReference):
            label = unicode(expr)
            try:
                reffed_expr = rule_map[label]
            except KeyError:
                raise UndefinedLabel(expr)
            return self._resolve_refs(rule_map, reffed_expr)
        else:
            original_members = getattr(expr, 'members', ())
            if original_members and not getattr(expr, 'is_resolved', False):
                # Prevents infinite recursion for circular refs. At worst, one
                # of `expr.members` can refer back to `expr`, but it can't go
                # any farther.
                expr.members = ()
                resolved_members = [self._resolve_refs(rule_map, member)
                                    for member in original_members]
                expr.members = resolved_members
                expr.is_resolved = True
            return expr

    def visit_rules(self, node, (_, rules)):
        """Collate all the rules into a map. Return (map, default rule).

        The default rule is the first one. Or, if you have more than one rule
        of that name, it's the last-occurring rule of that name. (This lets you
        override the default rule when you extend a grammar.) If there are no
        string-based rules, the default rule is None, because the custom rules,
        due to being kwarg-based, are unordered.

        """
        # Map each rule's name to its Expression. Later rules of the same name
        # override earlier ones. This lets us define rules multiple times and
        # have the last declaration win, so you can extend grammars by
        # concatenation.
        rule_map = dict((expr.name, expr) for expr in rules)

        # And custom rules override string-based rules. This is the least
        # surprising choice when you compare the dict constructor:
        # dict({'x': 5}, x=6).
        rule_map.update(self.custom_rules)

        # Resolve references. This tolerates forward references.
        rule_map = dict((expr.name, self._resolve_refs(rule_map, expr))
                        for expr in rule_map.itervalues())

        # isinstance() is a temporary hack around the fact that * rules don't
        # always get transformed into lists by NodeVisitor. We should fix that;
        # it's surprising and requires writing lame branches like this.
        return rule_map, (rule_map[rules[0].name]
                          if isinstance(rules, list) and rules else None)


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
