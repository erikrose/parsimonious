"""Tests to show that the benchmarks we based our speed optimizations on are still valid"""

from functools import partial
from timeit import timeit

from nose.tools import ok_


timeit = partial(timeit, number=500000)


def test_lists_vs_dicts():
    """See what's faster at int key lookup: dicts or lists."""
    list_time = timeit('item = l[9000]', 'l = [0] * 10000')
    dict_time = timeit('item = d[9000]', 'd = dict((x, 0) for x in xrange(10000))')

    # Dicts take about 1.6x as long as lists in Python 2.6 and 2.7.
    ok_(list_time < dict_time, '{0} < {1}'.format(list_time, dict_time))


def test_call_vs_inline():
    """How bad is the calling penalty?"""
    no_call = timeit('l[0] += 1', 'l = [0]')
    call = timeit('add(); l[0] += 1', 'l = [0]\n'
                                      'def add():\n'
                                      '    pass')

    # Calling a function is pretty fast; it takes just 1.2x as long as the
    # global var access and addition in l[0] += 1.
    ok_(no_call < call, '{0} (no call) < {1} (call)'.format(no_call, call))


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
        '{0} (startswith) < {1} (re)'.format(startswith_time, re_time))
