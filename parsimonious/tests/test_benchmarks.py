"""Tests to show that the benchmarks we based our speed optimizations on are
still valid"""

from functools import partial
from timeit import timeit
from unittest import TestCase

from nose.tools import ok_
try:
    from pyparsing import CaselessLiteral, Word, Group
    has_pyparsing = True
except ImportError:
    has_pyparsing = False

from parsimonious.grammar import Grammar


timeit = partial(timeit, number=500000)


def test_lists_vs_dicts():
    """See what's faster at int key lookup: dicts or lists."""
    list_time = timeit('item = l[9000]', 'l = [0] * 10000')
    dict_time = timeit('item = d[9000]', 'd = dict((x, 0) for x in range(10000))')

    # Dicts take about 1.6x as long as lists in Python 2.6 and 2.7.
    ok_(list_time < dict_time, '%s < %s' % (list_time, dict_time))


def test_call_vs_inline():
    """How bad is the calling penalty?"""
    no_call = timeit('l[0] += 1', 'l = [0]')
    call = timeit('add(); l[0] += 1', 'l = [0]\n'
                                      'def add():\n'
                                      '    pass')

    # Calling a function is pretty fast; it takes just 1.2x as long as the
    # global var access and addition in l[0] += 1.
    ok_(no_call < call, '%s (no call) < %s (call)' % (no_call, call))


def test_startswith_vs_regex():
    """Can I beat the speed of regexes by special-casing literals?"""
    re_time = timeit(
        'r.match(t, 19)',
        'import re\n'
        "r = re.compile('hello')\n"
        "t = 'this is the finest hello ever'")
    startswith_time = timeit("t.startswith('hello', 19)",
                             "t = 'this is the finest hello ever'")

    # Regexes take 2.24x as long as simple string matching.
    ok_(startswith_time < re_time,
        '%s (startswith) < %s (re)' % (startswith_time, re_time))


class VersusPyparsingTests(TestCase):
    def setup(self):
        """Run my tests only if pyparsing is installed.

        We don't want to actually depend on pyparsing in order to run the
        tests; that would be kind of lame.

        """
        if not has_pyparsing:
            raise SkipTest

    def parsimonious_grammar(self):
        return Grammar(r"""
            select = ~"select"i
            from = ~"from"i
            ident = ~"[a-zA-Z_\$]"
            column = ident ("." ident)*
            column_list = column (~", +" column)*
            columns = "*" / column_list
            table_list = column_list  # pyparsing refines this laboriously for
                                      # no apparent reason.
            statement = select columns from table_list ";"
            statements = statement (~"\n *" statement)
            """, default_rule='statements')

    def test_lots_of_sql(self):
        """Make sure we're faster at parsing the simpleSQL example from
        pyparsing's own tests.

        The only different is that we parse a large number of SQL statements
        all at once, because that's what I care about making fast: large bodies
        of text.

        """
        grammar = self.parsimonious_grammar()
        sql = ("""SELECT * from XYZZY, ABC;
               select * from SYS.XYZZY;
               Select A from Sys.dual;
               Select AA,BB,CC from Sys.dual;
               Select A, B, C from Sys.dual;
               Select A, B, C from Sys.dual;
               Select A, B, C frox Sys.dual;
               Select A, B, C from Sys.dual, Table2;
               """)
        print grammar.parse(sql)
