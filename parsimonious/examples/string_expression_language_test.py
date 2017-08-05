# -*- coding: utf-8 -*-
from nose.tools import eq_

from parsimonious.examples.string_expression_language import evaluate


def test_empty_program():
    evaluate("")
    evaluate("#X\n")
    evaluate("{}")
    evaluate("{#\n}")
    evaluate("# comment\n")
    evaluate(" { # comment \n} ")

def test_expressions():
    evaluate("{foo = 'bar'}")
    evaluate("{foo = 'abc' \n baz = 'def'}")

def test_evaluation():
    expected_result = {'foo': 'bar'}
    actual_result = evaluate("{foo = 'bar'}")
    eq_(expected_result, actual_result)

def test_expression_group_evaluation():
    expected_result = {'foo': 'abc', 'bar': 'xyz', 'baz': 'def', 'frob': 'abcxyzdef'}
    actual_result = evaluate(
        "    {   \n foo = 'abc' \n bar = 'xyz' \n baz = 'def' \n frob = foo + bar + baz \n }")
    eq_(expected_result, actual_result)

def test_full_program():
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
    actual_result = evaluate(program_text)
    eq_(expected_result, actual_result)
