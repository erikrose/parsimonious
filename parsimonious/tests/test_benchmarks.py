"""Tests to show that the benchmarks we based our speed optimizations on are still valid"""

from timeit import timeit


def test_lists_vs_dicts():
    """See what's faster at int key lookup: dicts or lists."""
    list_time = timeit('item = l[9000]', 'l = [0] * 10000')
    dict_time = timeit('item = d[9000]', 'd = dict((x, 0) for x in xrange(10000))')

    # Dicts take about 1.6x as long as lists in Python 2.6 and 2.7.
    print '%s < %s' % (list_time, dict_time)
    assert list_time < dict_time


def test_call_vs_inline():
    """How bad is the calling penalty?"""
    no_call = timeit('l[0] += 1', 'l = [0]')
    call = timeit('add(); l[0] += 1', 'l = [0]\n'
                                      'def add():\n'
                                      '    pass')

    # Calling a function is pretty fast; it takes just 1.2x as long as the
    # global var access and addition in l[0] += 1.
    print '%s (no call) < %s (call)' % (no_call, call)
    assert no_call < call
