from collections import namedtuple
from unittest import TestCase

from parsimonious import Grammar, NodeVisitor, ParseError, TokenGrammar
from parsimonious import expressions


class SeparatedTests(TestCase):
    def test_flat_items_and_positions(self):
        grammar = Grammar('items = item+ % comma\nitem = ~"[a-z]+"\ncomma = ","')
        node = grammar.parse('one,two,three')
        self.assertEqual(node.text, 'one,two,three')
        self.assertEqual([child.text for child in node.children], ['one', 'two', 'three'])
        self.assertEqual([child.expr_name for child in node.children], ['item'] * 3)
        self.assertEqual([(c.start, c.end) for c in node.children], [(0, 3), (4, 7), (8, 13)])

    def test_empty_and_single_lists(self):
        for quantifier in ('*', '+'):
            grammar = Grammar('items = "x"' + quantifier + ' % ","')
            self.assertEqual(len(grammar.parse('x').children), 1)
            if quantifier == '*':
                self.assertEqual(grammar.parse('').children, [])
            else:
                with self.assertRaises(ParseError):
                    grammar.parse('')

    def test_separator_is_rolled_back_when_item_is_missing(self):
        grammar = Grammar('items = "x"+ % ","')
        self.assertEqual(grammar.match('x,x,').end, 3)
        for text in (',x', 'x,', 'x,,x'):
            with self.subTest(text=text), self.assertRaises(ParseError):
                grammar.parse(text)
        # The comma is still available to an enclosing expression.
        Grammar('items = ("x"+ % ",") ","').parse('x,x,')

    def test_bounds_count_items_and_stop_before_next_separator(self):
        grammar = Grammar('items = "x"{2,3} % ","')
        self.assertEqual(len(grammar.parse('x,x').children), 2)
        self.assertEqual(len(grammar.parse('x,x,x').children), 3)
        self.assertEqual(grammar.match('x,x,x,x').end, 5)
        for text in ('', 'x', 'x,x,x,x'):
            with self.subTest(text=text), self.assertRaises(ParseError):
                grammar.parse(text)
        self.assertEqual(Grammar('items = "x"{0} % ","').parse('').end, 0)

    def test_grouping_lookahead_and_alternatives(self):
        grammar = Grammar('''
            root = &(item+ % separator) (item+ % separator) "!" / "empty"
            item = "a" / "b"
            separator = "," ~" *"
        ''')
        grammar.parse('a, b,a!')
        grammar.parse('empty')
        Grammar('root = ("a" / "b")+ % ("," " "?)').parse('a, b,a')

    def test_visitors_see_only_items(self):
        class Visitor(NodeVisitor):
            grammar = Grammar('items = number+ % ","\nnumber = ~"[0-9]+"')

            def visit_number(self, node, children):
                return int(node.text)

            def visit_items(self, node, children):
                return children

        self.assertEqual(Visitor().parse('1,20,300'), [1, 20, 300])

    def test_recursive_references(self):
        grammar = Grammar('''
            array = "[" (value* % ",") "]"
            value = array / ~"[0-9]+"
        ''')
        grammar.parse('[1,[],[2,3]]')

    def test_round_trip_grammar_and_equality(self):
        grammar = Grammar('root = "[" (item{1,3} % ("," " "?)) "]"\nitem = "x"')
        rebuilt = Grammar(str(grammar))
        self.assertEqual(grammar, rebuilt)
        rebuilt.parse('[x, x,x]')
        a, comma, semicolon = map(expressions.Literal, ['a', ',', ';'])
        first = expressions.Separated(a, comma, min=1)
        self.assertEqual(first, expressions.Separated(a, comma, min=1))
        self.assertNotEqual(first, expressions.Separated(a, comma, min=2))
        self.assertNotEqual(first, expressions.Separated(a, semicolon, min=1))

    def test_bytes_and_unicode(self):
        grammar = Grammar('items = b"a"+ % b","')
        self.assertEqual([c.text for c in grammar.parse(b'a,a').children], [b'a', b'a'])
        grammar = Grammar('items = "\u03bb"+ % ","')
        self.assertEqual(len(grammar.parse('\u03bb,\u03bb').children), 2)

    def test_token_grammar_and_end_of_input(self):
        token = namedtuple('Token', 'type value')
        grammar = TokenGrammar('items = "number"+ % "comma"')
        source = [token('number', 1), token('comma', ','), token('number', 2)]
        node = grammar.parse(source)
        self.assertEqual([c.start for c in node.children], [0, 2])
        for invalid in ([], source[:2]):
            with self.subTest(source=invalid), self.assertRaises(ParseError):
                grammar.parse(invalid)

    def test_zero_width_expressions_terminate(self):
        for text in ('', 'a'):
            node = Grammar('items = ""+ % ""').match(text)
            self.assertEqual(node.end, 0)
            self.assertEqual(len(node.children), 1)
        node = Grammar('items = ""{2,4} % ""').parse('')
        self.assertEqual(len(node.children), 2)
        node = Grammar('items = "a"+ % ""').parse('aaa')
        self.assertEqual(len(node.children), 3)

    def test_many_items_do_not_use_recursive_list_rules(self):
        source = ','.join(['x'] * 10000)
        self.assertEqual(len(Grammar('items = "x"+ % ","').parse(source).children), 10000)

    def test_missing_item_reports_the_item_position(self):
        grammar = Grammar('items = item{2} % ","\nitem = ~"[0-9]+"')
        with self.assertRaises(ParseError) as raised:
            grammar.parse('1,no')
        self.assertEqual(raised.exception.pos, 2)
        self.assertEqual(raised.exception.expr, grammar['item'])

    def test_comments_and_whitespace_in_syntax(self):
        Grammar('items = "x"+ # items\n % # separator\n ","').parse('x,x')

    def test_percentage_literal_is_unchanged(self):
        Grammar('literal = "%"').parse('%')
