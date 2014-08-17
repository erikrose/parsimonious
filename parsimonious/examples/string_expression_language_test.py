# -*- coding: utf-8 -*-
import unittest
from parsimonious.examples.string_expression_language import StringExpressionLanguage


class StringExpressionLanguageTest(unittest.TestCase):

    def setUp(self):
        self.string_expression_language = StringExpressionLanguage()

    def test_empty_program(self):
        self.string_expression_language.evaluate("")
        self.string_expression_language.evaluate("#X\n")
        self.string_expression_language.evaluate("{}")
        self.string_expression_language.evaluate("{#\n}")
        self.string_expression_language.evaluate("# comment\n")
        self.string_expression_language.evaluate(" { # comment \n} ")

    def test_expressions(self):
        self.string_expression_language.evaluate("{foo = 'bar'}")
        self.string_expression_language.evaluate("{foo = 'abc' \n baz = 'def'}")
        self.string_expression_language.evaluate("{foo = 'abc' \n baz = 'def' \n frob = foo baz }")

