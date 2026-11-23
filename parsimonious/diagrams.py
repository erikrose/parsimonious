"""Optional SVG railroad diagrams for compiled PEG grammars."""

from collections import OrderedDict
from io import StringIO

from parsimonious import expressions as peg
from parsimonious.grammar import Grammar


def convert_grammar_to_diagram(grammar, collapsible=(), engine='railroad_diagrams'):
    """Return rule names mapped to standalone UTF-8 SVG bytes in grammar order.

    Install ``parsimonious[railroad]`` to use this function. Rule references are
    boxes unless their names occur in ``collapsible``, in which case their
    expressions are expanded in place. Recursive references always remain boxes.
    Aliases of the same compiled expression share its canonical reference name.

    Ordered choices run from top to bottom. Lookahead is labelled as zero-width;
    bounded repetition is labelled with its permitted count rather than expanded
    into a potentially enormous diagram. Custom parsers are opaque boxes and are
    never called. Only the portable ``railroad_diagrams`` engine is supported.
    """
    if not isinstance(grammar, Grammar):
        raise TypeError('grammar must be a Grammar or TokenGrammar')
    if engine != 'railroad_diagrams':
        raise ValueError('the only supported engine is railroad_diagrams')
    if isinstance(collapsible, (str, bytes)):
        raise TypeError('collapsible must be an iterable of rule names')
    collapsible = set(collapsible)
    unknown = collapsible.difference(grammar)
    if unknown:
        raise ValueError('unknown collapsible rules: ' + ', '.join(sorted(unknown)))

    # Import lazily so importing this module or using the parser adds no dependency.
    try:
        import railroad
    except ImportError as error:
        if error.name != 'railroad':
            raise
        raise ImportError('SVG diagrams require pip install "parsimonious[railroad]"') from error

    names = {}
    for name, expression in grammar.items():
        names.setdefault(id(expression), name)
        if expression.name == name:
            names[id(expression)] = name
    expandable = {id(grammar[name]) for name in collapsible}

    def render(expression, active, root=False):
        identity = id(expression)
        name = names.get(identity)
        if identity in active:
            return railroad.NonTerminal(name or expression.name or 'recursive expression')
        if name is not None and not root and identity not in expandable:
            return railroad.NonTerminal(name)
        active = active | {identity}

        if isinstance(expression, peg.TokenMatcher):
            return railroad.Terminal(repr(expression.literal), title='token type')
        if isinstance(expression, peg.Literal):
            return railroad.Skip() if not expression.literal else railroad.Terminal(repr(expression.literal))
        if isinstance(expression, peg.Regex):
            return railroad.Terminal(expression._as_rhs(), title='regular expression')
        if isinstance(expression, peg.Sequence):
            children = [render(member, active) for member in expression.members]
            return railroad.Sequence(*children) if children else railroad.Skip()
        if isinstance(expression, peg.OneOf):
            children = [render(member, active) for member in expression.members]
            if not children:
                return railroad.NonTerminal('never matches', title='empty ordered choice')
            return railroad.Group(railroad.Choice(0, *children), 'ordered choice')
        if isinstance(expression, peg.Lookahead):
            label = 'negative lookahead (zero-width)' if expression.negativity else 'lookahead (zero-width)'
            return railroad.Group(render(expression.members[0], active), label)
        if isinstance(expression, peg.Quantifier):
            minimum, maximum = expression.min, expression.max
            if minimum < 0 or maximum < minimum:
                raise ValueError('invalid repetition bounds')
            if maximum == 0:
                return railroad.Skip()
            child = render(expression.members[0], active)
            if maximum == 1:
                return railroad.Optional(child) if minimum == 0 else child
            if maximum == float('inf'):
                if minimum == 0:
                    return railroad.ZeroOrMore(child)
                if minimum == 1:
                    return railroad.OneOrMore(child)
                label = 'repeat {} or more times'.format(minimum)
            elif minimum == maximum:
                label = 'repeat {} times'.format(minimum)
            else:
                label = 'repeat {}..{} times'.format(minimum, maximum)
            repeated = railroad.OneOrMore(child)
            if minimum == 0:
                repeated = railroad.Optional(repeated)
            return railroad.Group(repeated, label)
        return railroad.NonTerminal(expression.name or type(expression).__name__, title='custom parser (opaque)')

    diagrams = OrderedDict()
    for name, expression in grammar.items():
        output = StringIO()
        railroad.Diagram(render(expression, set(), root=True)).writeStandalone(output.write)
        diagrams[name] = output.getvalue().encode('utf-8')
    return diagrams
