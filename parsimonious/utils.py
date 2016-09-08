"""General tools which don't depend on other parts of Parsimonious"""

import ast
from sys import version_info

from six import python_2_unicode_compatible


class StrAndRepr(object):
    """Mix-in to add a ``__str__`` and ``__repr__`` which return the
    UTF-8-encoded value of ``__unicode__``"""

    if version_info >= (3,):
        # Don't return the "bytes" type from Python 3's __str__:
        def __repr__(self):
            return self.__str__()
    else:
        def __repr__(self):
            return self.__str__().encode('utf-8')


def evaluate_string(string):
    """Piggyback on Python's string support so we can have backslash escaping
    and niceties like \n, \t, etc. string.decode('string_escape') would have
    been a lower-level possibility.

    """
    return ast.literal_eval(string)


@python_2_unicode_compatible
class Token(StrAndRepr):
    """A class to represent tokens, for use with TokenGrammars

    You will likely want to subclass this to hold additional information, like
    the characters that you lexed to create this token. Alternately, feel free
    to create your own class from scratch. The only contract is that tokens
    must have a ``type`` attr.

    """
    __slots__ = ['type']

    def __init__(self, type):
        self.type = type

    def __str__(self):
        return u'<Token "%s">' % (self.type,)

    def __eq__(self, other):
        return self.type == other.type
