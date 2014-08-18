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

    def test_evaluation(self):
        expected_result = {'foo': 'bar'}
        actual_result = self.string_expression_language.evaluate("{foo = 'bar'}")
        self.assertEqual(expected_result, actual_result)


    def test_expression_group_evaluation(self):
        expected_result = {'foo': 'abc', 'bar': 'xyz', 'baz': 'def', 'frob': 'abcxyzdef'}
        actual_result = self.string_expression_language.evaluate(
            "    {   \n foo = 'abc' \n bar = 'xyz' \n baz = 'def' \n frob = foo + bar + baz \n }")
        self.assertEqual(expected_result, actual_result)

    def test_full_program(self):
        program_text = """
            {
                # a test program
                part1 = 'frog'
                part2 = 'cat'
                part3 = 'lizard'
                part4 = 'fish'
                part4 = 'dragon'       # overwrites fish
                part5 = part4 + part2
                space = ' '
                animals = part1 + space + part2 + space + part5
            }

        """
        expected_result = {"part1": "frog", "part2": "cat", "part3": "lizard", "part4": "dragon", "space": " ",
                            "part5": "dragoncat",
                            "animals": "frog cat dragoncat"}
        actual_result = self.string_expression_language.evaluate(program_text)
        self.assertEqual(expected_result, actual_result)

