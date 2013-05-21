r"""# JSON grammar

value = space (string / number / object / array / true_false_null) space

object = "{" members "}"
members = (pair ("," pair)*)?
pair = string ":" value
array = "[" elements "]"
elements = (value ("," value)*)?
true_false_null = "true" / "false" / "null"

string = space "\"" chars "\"" space
chars = ~"[^\"]*"  # TODO implement the real thing
number = (int frac exp) / (int exp) / (int frac) / int
int = "-"? ((digit1to9 digits) / digit)
frac = "." digits
exp = e digits
digits = digit+
e = "e+" / "e-" / "e" / "E+" / "E-" / "E"

digit1to9 = ~"[1-9]"
digit = ~"[0-9]"
space = ~"\s*"

"""
from parsimonious.grammar import Grammar


class JSONDecoder(object):

    def loads(self, node):
        if isinstance(node, str):
            node = Grammar(__doc__).parse(node)
        method = getattr(self, node.expr_name, self.default)
        return method(node, [self.loads(n) for n in node])

    def default(self, node, children):
        return children

    def value(self, node, children):
        return children[1][0]

    def object(self, node, children):
        return children[1]

    def members(self, node, children):
        if not children:
            return {}
        head, tail = children[0][:1], children[0][1:][0]
        return dict(head + [el[1] for el in tail])

    def pair(self, node, children):
        return children[0], children[2]

    def array(self, node, children):
        return children[1]

    def elements(self, node, children):
        if not children:
            return []
        head, tail = children[0][:1], children[0][1:][0]
        return head + [el[1] for el in tail]

    def true_false_null(self, node, children):
        return {'true': True, 'false': False, 'null': None}[node.text.strip()]

    def number(self, node, children):
        return float(node.text.strip())

    def string(self, node, children):
        return node.text.strip().strip('"')  # TODO implement the real thing


json = JSONDecoder()
