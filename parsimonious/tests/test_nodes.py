# -*- coding: utf-8 -*-
from unittest import SkipTest, TestCase
from parsimonious import Grammar, NodeVisitor, VisitationError, rule
from parsimonious.expressions import Literal, Regex
from parsimonious.grammar import TokenGrammar
from parsimonious.nodes import Node, RegexNode
from parsimonious.utils import Token


class HtmlFormatter(NodeVisitor):
    """Visitor that turns a parse tree into HTML fragments"""

    grammar = Grammar("""bold_open  = '(('""")  # just partial

    def visit_bold_open(self, node, visited_children):
        return '<b>'

    def visit_bold_close(self, node, visited_children):
        return '</b>'

    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text

    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)


class ExplosiveFormatter(NodeVisitor):
    """Visitor which raises exceptions"""

    def visit_boom(self, node, visited_children):
        raise ValueError


class SimpleTests(TestCase):
    def test_visitor(self):
        """Assert a tree gets visited correctly."""
        grammar = Grammar(r'''
            bold_text  = bold_open text bold_close
            text       = ~'[a-zA-Z 0-9]*'
            bold_open  = '(('
            bold_close = '))'
        ''')
        text = '((o hai))'
        tree = Node(grammar['bold_text'], text, 0, 9,
                    [Node(grammar['bold_open'], text, 0, 2),
                     Node(grammar['text'], text, 2, 7),
                     Node(grammar['bold_close'], text, 7, 9)])
        self.assertEqual(grammar.parse(text), tree)
        result = HtmlFormatter().visit(tree)
        self.assertEqual(result, '<b>o hai</b>')


    def test_visitation_exception(self):
        self.assertRaises(VisitationError,
                      ExplosiveFormatter().visit,
                      Node(Literal(''), '', 0, 0))


    def test_str(self):
        """Test str and unicode of ``Node``."""
        n = Node(Literal('something', name='text'), 'o hai', 0, 5)
        good = '<Node called "text" matching "o hai">'
        self.assertEqual(str(n), good)


    def test_repr(self):
        """Test repr of ``Node``."""
        s = 'hai ö'
        boogie = 'böogie'
        n = Node(Literal(boogie), s, 0, 3, children=[
                Node(Literal(' '), s, 3, 4), Node(Literal('ö'), s, 4, 5)])
        self.assertEqual(repr(n),
            str("""s = {hai_o}\nNode({boogie}, s, 0, 3, children=[Node({space}, s, 3, 4), Node({o}, s, 4, 5)])""").format(
                hai_o=repr(s),
                boogie=repr(Literal(boogie)),
                space=repr(Literal(" ")),
                o=repr(Literal("ö")),
            )
        )

    def test_parse_shortcut(self):
        """Exercise the simple case in which the visitor takes care of parsing."""
        self.assertEqual(HtmlFormatter().parse('(('), '<b>')


    def test_match_shortcut(self):
        """Exercise the simple case in which the visitor takes care of matching."""
        self.assertEqual(HtmlFormatter().match('((other things'), '<b>')


class NodeTruthinessTests(TestCase):
    """A node's truth value describes whether it consumed input."""

    def test_absent_optional_and_repeated_nodes(self):
        for suffix in ('?', '*'):
            with self.subTest(suffix=suffix):
                node = Grammar("value = 'a'" + suffix).parse('')
                self.assertIsInstance(node, Node)
                self.assertEqual((node.start, node.end), (0, 0))
                self.assertEqual(node.children, [])
                self.assertFalse(node)

    def test_empty_match_at_nonzero_offset(self):
        for empty, text in (('', 'ab'), (b'', b'ab')):
            with self.subTest(text=text):
                node = Literal(empty).match(text, pos=1)
                self.assertEqual((node.start, node.end), (1, 1))
                self.assertEqual(node.text, empty)
                self.assertFalse(node)

    def test_nonempty_leaf_nodes(self):
        for text in ('枚', b'\x00'):
            with self.subTest(text=text):
                node = Literal(text).parse(text)
                self.assertEqual((node.start, node.end), (0, 1))
                self.assertEqual(node.children, [])
                self.assertTrue(node)

    def test_regex_nodes_follow_match_span(self):
        expression = Regex('a*')
        present = expression.match('baaa', pos=1)
        self.assertIsInstance(present, RegexNode)
        self.assertEqual(present.match.span(), (1, 4))
        self.assertTrue(present)

        absent = expression.match('b', pos=1)
        self.assertIsInstance(absent, RegexNode)
        self.assertEqual((absent.start, absent.end), (1, 1))
        self.assertEqual(absent.match.span(), (1, 1))
        self.assertFalse(absent)

    def test_token_nodes_follow_token_span(self):
        grammar = TokenGrammar('value = "long_token_name"?')
        present = grammar.parse([Token('long_token_name')])
        self.assertEqual((present.start, present.end), (0, 1))
        self.assertTrue(present)
        self.assertTrue(present.children[0])

        absent = grammar.match([Token('other')], pos=1)
        self.assertEqual((absent.start, absent.end), (1, 1))
        self.assertFalse(absent)

    def test_visitor_can_use_node_truthiness(self):
        class OptionalValueVisitor(NodeVisitor):
            grammar = Grammar('value = "a"?')

            def visit_value(self, node, visited_children):
                if not node:
                    return []
                return [node.text]

            def generic_visit(self, node, visited_children):
                return node.text

        visitor = OptionalValueVisitor()
        self.assertEqual(visitor.parse('a'), ['a'])
        self.assertEqual(visitor.parse(''), [])

    def test_zero_width_nodes_with_children(self):
        tree = Grammar('value = (&"a")? &"a"').match('a')
        self.assertEqual(len(tree.children), 2)
        self.assertEqual(len(tree.children[0].children), 1)
        for node in [tree] + tree.children:
            with self.subTest(expression=type(node.expr).__name__):
                self.assertEqual((node.start, node.end), (0, 0))
                self.assertFalse(node)

    def test_zero_width_matches_remain_parse_successes(self):
        examples = (
            ('value = ("" / "x") "a"', 'a'),
            ('value = (&"a")+ "a" !"a"', 'a'),
            ('value = ""', ''),
        )
        for rules, text in examples:
            with self.subTest(rules=rules):
                node = Grammar(rules).parse(text)
                self.assertIsInstance(node, Node)
                self.assertEqual((node.start, node.end), (0, len(text)))
                self.assertEqual(node.text, text)


class CoupledFormatter(NodeVisitor):
    @rule('bold_open text bold_close')
    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)

    @rule('"(("')
    def visit_bold_open(self, node, visited_children):
        return '<b>'

    @rule('"))"')
    def visit_bold_close(self, node, visited_children):
        return '</b>'

    @rule('~"[a-zA-Z 0-9]*"')
    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text

class DecoratorTests(TestCase):
    def test_rule_decorator(self):
        """Make sure the @rule decorator works."""
        self.assertEqual(CoupledFormatter().parse('((hi))'), '<b>hi</b>')


    def test_rule_decorator_subclassing(self):
        """Make sure we can subclass and override visitor methods without blowing
        away the rules attached to them."""
        class OverridingFormatter(CoupledFormatter):
            def visit_text(self, node, visited_children):
                """Return the text capitalized."""
                return node.text.upper()

            @rule('"not used"')
            def visit_useless(self, node, visited_children):
                """Get in the way. Tempt the metaclass to pave over the
                superclass's grammar with a new one."""

        raise SkipTest("I haven't got around to making this work yet.")
        self.assertEqual(OverridingFormatter().parse('((hi))'), '<b>HI</b>')


class PrimalScream(Exception):
    pass


class SpecialCasesTests(TestCase):
    def test_unwrapped_exceptions(self):
        class Screamer(NodeVisitor):
            grammar = Grammar("""greeting = 'howdy'""")
            unwrapped_exceptions = (PrimalScream,)

            def visit_greeting(self, thing, visited_children):
                raise PrimalScream('This should percolate up!')

        self.assertRaises(PrimalScream, Screamer().parse, 'howdy')


    def test_node_inequality(self):
        node = Node(Literal('12345'), 'o hai', 0, 5)
        self.assertTrue(node != 5)
        self.assertTrue(node != None)
        self.assertTrue(node != Node(Literal('23456'), 'o hai', 0, 5))
        self.assertTrue(not (node != Node(Literal('12345'), 'o hai', 0, 5)))


    def test_generic_visit_NotImplementedError_unnamed_node(self):
        """
        Test that generic_visit provides informative error messages
        when visitors are not defined.

        Regression test for https://github.com/erikrose/parsimonious/issues/110
        """
        class MyVisitor(NodeVisitor):
            grammar = Grammar(r'''
                bar = "b" "a" "r"
            ''')
            unwrapped_exceptions = (NotImplementedError, )

        with self.assertRaises(NotImplementedError) as e:
            MyVisitor().parse('bar')
        self.assertIn("No visitor method was defined for this expression: 'b'", str(e.exception))


    def test_generic_visit_NotImplementedError_named_node(self):
        """
        Test that generic_visit provides informative error messages
        when visitors are not defined.
        """
        class MyVisitor(NodeVisitor):
            grammar = Grammar(r'''
                bar = myrule myrule myrule
                myrule = ~"[bar]"
            ''')
            unwrapped_exceptions = (NotImplementedError, )

        with self.assertRaises(NotImplementedError) as e:
            MyVisitor().parse('bar')
        self.assertIn("No visitor method was defined for this expression: myrule = ~'[bar]'", str(e.exception))
