# -*- coding: utf-8 -*-
from unittest import TestCase
from parsimonious import Grammar, NodeVisitor, VisitationError, rule
from parsimonious.expressions import Literal
from parsimonious.nodes import Node


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

        self.assertEqual(OverridingFormatter().parse('((hi))'), '<b>HI</b>')

    def test_override_without_rule(self):
        class UpperFormatter(CoupledFormatter):
            def visit_text(self, node, visited_children):
                return node.text.upper()

        self.assertEqual(UpperFormatter().parse('((hi))'), '<b>HI</b>')

    def test_redecorate_inherited_rule(self):
        class NumericFormatter(CoupledFormatter):
            @rule('~"[0-9]+"')
            def visit_text(self, node, visited_children):
                return int(node.text)

            def visit_bold_text(self, node, visited_children):
                opening, number, closing = visited_children
                return opening + str(number + 1) + closing

        self.assertEqual(NumericFormatter().parse('((12))'), '<b>13</b>')
        self.assertEqual(CoupledFormatter().parse('((hi))'), '<b>hi</b>')

    def test_new_rule_referenced_by_override(self):
        class BracketFormatter(CoupledFormatter):
            @rule('bracket_open text bold_close')
            def visit_bold_text(self, node, visited_children):
                return ''.join(visited_children)

            @rule('"[["')
            def visit_bracket_open(self, node, visited_children):
                return '<strong>'

        self.assertEqual(BracketFormatter().parse('[[hi))'), '<strong>hi</b>')

    def test_two_generations_preserve_undecorated_override(self):
        class UpperFormatter(CoupledFormatter):
            def visit_text(self, node, visited_children):
                return node.text.upper()

        class ChildFormatter(UpperFormatter):
            @rule('"extra"')
            def visit_extra(self, node, visited_children):
                return node.text

        self.assertEqual(ChildFormatter().parse('((hi))'), '<b>HI</b>')
        self.assertEqual(ChildFormatter().match('((hi)) trailing'), '<b>HI</b>')

    def test_two_generations_preserve_decorated_override(self):
        class SquareFormatter(CoupledFormatter):
            @rule('"[["')
            def visit_bold_open(self, node, visited_children):
                return '<strong>'

        class ChildFormatter(SquareFormatter):
            @rule('"extra"')
            def visit_extra(self, node, visited_children):
                return node.text

        self.assertEqual(ChildFormatter().parse('[[hi))'), '<strong>hi</b>')

    def test_sibling_rules_are_independent(self):
        class SquareFormatter(CoupledFormatter):
            @rule('"[["')
            def visit_bold_open(self, node, visited_children):
                return '<strong>'

        class AngleFormatter(CoupledFormatter):
            @rule('"<<"')
            def visit_bold_open(self, node, visited_children):
                return '<em>'

        self.assertEqual(SquareFormatter().parse('[[hi))'), '<strong>hi</b>')
        self.assertEqual(AngleFormatter().parse('<<hi))'), '<em>hi</b>')
        self.assertEqual(CoupledFormatter().parse('((hi))'), '<b>hi</b>')

    def test_inherited_default_precedes_subclass_source_location(self):
        # The subclass rule's function is defined before the parent root.
        @rule('"unused"')
        def visit_unused(self, node, visited_children):
            return 'unused'

        class Parent(NodeVisitor):
            @rule('"root"')
            def visit_root(self, node, visited_children):
                return 'root'

        class Child(Parent):
            visit_extra = visit_unused

        self.assertEqual(Child().parse('root'), 'root')

    def test_diamond_uses_nearest_rule_definition(self):
        class Left(CoupledFormatter):
            @rule('"left"')
            def visit_left(self, node, visited_children):
                return node.text

        class Right(CoupledFormatter):
            @rule('"[["')
            def visit_bold_open(self, node, visited_children):
                return '<strong>'

        class Child(Left, Right):
            @rule('"child"')
            def visit_child(self, node, visited_children):
                return node.text

        self.assertEqual(Child().parse('[[hi))'), '<strong>hi</b>')
        self.assertEqual(Left().parse('((hi))'), '<b>hi</b>')

    def test_multiple_inheritance_uses_leftmost_override(self):
        class Left(CoupledFormatter):
            @rule('"[["')
            def visit_bold_open(self, node, visited_children):
                return '<strong>'

        class Right(CoupledFormatter):
            @rule('"<<"')
            def visit_bold_open(self, node, visited_children):
                return '<em>'

        class Child(Left, Right):
            @rule('"child"')
            def visit_child(self, node, visited_children):
                return node.text

        self.assertEqual(Child().parse('[[hi))'), '<strong>hi</b>')

    def test_explicit_grammar_is_inherited_without_new_rules(self):
        class Explicit(CoupledFormatter):
            grammar = Grammar('text = "explicit"')

        class Child(Explicit):
            def visit_text(self, node, visited_children):
                return node.text.upper()

        self.assertEqual(Child().parse('explicit'), 'EXPLICIT')

    def test_explicit_grammar_starts_a_new_decorator_family(self):
        class Explicit(CoupledFormatter):
            grammar = Grammar('text = "explicit"')

        class Child(Explicit):
            @rule('"child"')
            def visit_child(self, node, visited_children):
                return node.text

        class Grandchild(Child):
            @rule('"extra"')
            def visit_extra(self, node, visited_children):
                return node.text

        self.assertEqual(Child().parse('child'), 'child')
        self.assertEqual(Grandchild().parse('child'), 'child')
        self.assertEqual(set(Grandchild.grammar), {'child', 'extra'})

    def test_decorators_still_replace_same_class_explicit_grammar(self):
        class Explicit(NodeVisitor):
            grammar = Grammar('manual = "manual"')

            @rule('"decorated"')
            def visit_decorated(self, node, visited_children):
                return node.text

        self.assertEqual(Explicit().parse('decorated'), 'decorated')

    def test_undecorated_mixin_preserves_inherited_grammar(self):
        class Mixin:
            def visit_text(self, node, visited_children):
                return node.text.upper()

        class Child(Mixin, CoupledFormatter):
            @rule('"extra"')
            def visit_extra(self, node, visited_children):
                return node.text

        self.assertEqual(Child().parse('((hi))'), '<b>HI</b>')

    def test_subclass_hook_sees_finished_grammar(self):
        observed = []

        class Parent(CoupledFormatter):
            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__(**kwargs)
                observed.append(cls().parse('[[hi))'))

        class Child(Parent):
            @rule('"[["')
            def visit_bold_open(self, node, visited_children):
                return '<strong>'

        self.assertEqual(observed, ['<strong>hi</b>'])

    def test_unrelated_explicit_grammar_does_not_hide_parent_rules(self):
        class Explicit(CoupledFormatter):
            grammar = Grammar('manual = "manual"')

        class Left(CoupledFormatter):
            @rule('"left"')
            def visit_left(self, node, visited_children):
                return node.text

        class Child(Left, Explicit):
            @rule('"extra"')
            def visit_extra(self, node, visited_children):
                return node.text

        self.assertEqual(Child().parse('((hi))'), '<b>hi</b>')


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
