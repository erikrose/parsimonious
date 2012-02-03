"""Subexpressions that make up a parsed grammar"""

# TODO: Make sure all symbol refs are local--not class lookups or
# anything--for speed. And kill all the dots.

import re


class Expression(object):
    """A thing that can be matched against a piece of text"""

    # Slots are about twice as fast as __dict__-based attributes:
    # http://stackoverflow.com/questions/1336791/dictionary-vs-object-which-is-more-efficient-and-why
    __slots__ = []

    def parse(self, text):
        """Return a parse tree of ``text``.

        Initialize the packrat cache and kick off the first ``match()`` call.

        """
        # The packrat cache. {expr: [length matched at text index 0,
        #                            length matched at text index 1, ...],
        #                     ...}
        cache = {}

        return self.match(text, 0, cache)
        # TODO: Freak out if the text didn't parse completely: if we didn't get
        # all the way to the end.

    # TODO: Make match() return a bit of the parse tree that the caller can
    # stitch together.
    def match(self, text, pos, cache):
        """Return length of match, ``None`` if no match.

        Check the cache first.

        """
        # TODO: Optimize. Probably a hot spot.
        # Is there a way of lookup up cached stuff that's faster than hashing
        # this id-pos pair?
        expr_id = id(self)
        cached = cache.get((expr_id, pos), ())
        if cached is not ():
            return cached
        match = self._match(text, pos, cache)
        cache[(expr_id, pos)] = match
        return match


class Regex(Expression):
    """An expression that matches what a regex does.

    Use these as much as you can and jam as much into each one as you can;
    they're fast.

    """
    __slots__ = ['re']

    def __init__(self, pattern):
        self.re = re.compile(pattern)

    def _match(self, text, pos, cache):
        """Return length of match, ``None`` if no match."""
        m = self.re.match(text, pos)
        if m is not None:
            span = m.span()
            return span[1] - span[0]


class Sequence(Expression):
    """A series of expressions that must match contiguous, ordered pieces of the text

    In other words, it's a concatenation operator: each piece has to match, one
    after another.

    """
    __slots__ = ['members']

    def __init__(self, members):
        """``members`` is a sequence of expressions."""
        self.members = members

    def _match(self, text, pos, cache):
        new_pos = pos
        length_of_sequence = 0
        for m in self.members:
            length = m.match(text, new_pos, cache)
            if length is None:
                return None
            new_pos += length
            length_of_sequence += length
        # Hooray! We got through all the members!
        return length_of_sequence
