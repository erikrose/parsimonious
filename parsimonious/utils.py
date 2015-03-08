"""General tools which don't depend on other parts of Parsimonious"""

import ast
from sys import version_info


class StrAndRepr(object):
    """Mix-in to add a ``__str__`` and ``__repr__`` which return the
    UTF-8-encoded value of ``__unicode__``"""

    if version_info >= (3,):
        # Don't return the "bytes" type from Python 3's __str__:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    __repr__ = __str__  # Language spec says must be string, not unicode.


def evaluate_string(string):
    """Piggyback on Python's string support so we can have backslash escaping
    and niceties like \n, \t, etc. string.decode('string_escape') would have
    been a lower-level possibility.

    """
    return ast.literal_eval(string)


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

    def __unicode__(self):
        return u'<Token "%s">' % (self.type,)

    def __eq__(self, other):
        return self.type == other.type
