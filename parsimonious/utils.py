"""General tools which don't depend on other parts of Parsimonious"""


class StrAndRepr(object):
    """Mix-in to add a ``__str__`` and ``__repr__`` which return the
    UTF-8-encoded value of ``__unicode__``"""

    def __str__(self):
        return self.__unicode__().encode('utf-8')

    __repr__ = __str__  # Language spec says must be string, not unicode.
