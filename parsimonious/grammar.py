# -*- coding: utf-8 -*-
"""The fastest pure-Python PEG parser I could muster"""


from parsimonious.expressions import *


class Grammar(object):
    """A collection of rules that describe a language

    You can start parsing from any of them, just by grabbing one as if out of a
    dict::

        g = Grammar('Greeting       = Hi | Hello'
                    'PoliteGreeting = Greeting, my good sir')
        g['Greeting'].parse('Hello')

    """
    def __init__(self, peg):
        # Maybe we should keep the original PEG text around in case people want to
        # extend already-compiled grammars. We can't rely on callers to nicely
        # expose their PEG strings. We can either have extending callers pull
        # the text off Grammar.peg, or we could get fancy and define __add__ on
        # Grammars and strings.
        self._rules = self._rules_from_peg(peg)

    def _rules_from_peg(self, peg):
        """Return a dict of rule names pointing to their expressions.

        It's a web of expressions, all referencing each other. Typically,
        there's a single root to the web of references, and that root is the
        starting symbol for parsing, but there's nothing saying you can't have
        multiple roots.

        """
        rules = {}  # Hard-code the objects, to bootstrap. {'rule name': Expression}
        # TODO: Remember to set each top-level expression's .name.
        # TODO: Unstub.
