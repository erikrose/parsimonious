"""A convenience which constructs expression trees from an easy-to-read EBNF-like syntax

Use this unless you have a compelling reason not to; it performs some
optimizations that would be tedious to do when constructing an expression tree
by hand.

"""
from parsimonious.expressions import *


class Grammar(dict):
    """A collection of expressions that describe a language

    You can start parsing from any of them, just by grabbing one as if out of a
    dict::

        g = Grammar('greeting        = Hi / Hello'
                    'polite_greeting = greeting ", my good sir"')
        g['polite_greeting'].parse('Hello, my good sir')

    You could also just construct a bunch of ``Expression`` objects yourself
    and stitch them together into a language, but this has some important
    advantages:

    * Languages are much easier to define in the domain-specific syntax this
      reads.
    * This does all kinds of whizzy space- and time-saving optimizations, like
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
        literal = Regex(r'"[^"]+"')
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
        eol = Regex(r'[\r\n]')  # TODO: Support $.
        rule = Sequence(Optional(ws), label, Optional(_), Literal('='), Optional(_), rhs, Optional(_), eol)
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
peg_grammar = Grammar('''
    rules = rule+ ws?
    rule = ws? label _? "=" _? rhs _? eol
    eol = ~r'[\r\n]'  # TODO: $
    rhs = poly_term / term
    poly_term = anded / ored / sequence
    anded = term and_term+
    and_term = _ "&" another_term
    ored = term or_term+
    or_term = _ "/" another_term
    sequence = term another_term+
    another_term = _ term
    term = quantified / atom
    quantified = atom quantifier
    atom = label / literal / regex
    regex = "~" literal ~"[ilmsux]*"i
    literal = ~r"\"[^\"]+""
    quantifier = ~"[*+?]"
    label = ~"[a-zA-Z_][a-zA-Z_0-9]*"
    _ = ~r"[ \t]+"  # horizontal whitespace
    ws = ~r"\s+"
    ''')
