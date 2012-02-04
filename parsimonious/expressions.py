"""Subexpressions that make up a parsed grammar"""

# TODO: Make sure all symbol refs are local--not class lookups or
# anything--for speed. And kill all the dots.

import re


__all__ = ['Literal', 'Regex', 'Sequence', 'OneOf', 'AllOf', 'Not', 'Optional',
           'ZeroOrMore', 'OneOrMore']


class _DummyCache(object):
    """Fake cache that always misses.

    This never gets used except in tests.

    """
    def get(self, key, default=None):
        return default

    def __setitem__(self, key, value):
        pass

dummy_cache = _DummyCache()


class Expression(object):
    """A thing that can be matched against a piece of text"""

    # Slots are about twice as fast as __dict__-based attributes:
    # http://stackoverflow.com/questions/1336791/dictionary-vs-object-which-is-more-efficient-and-why
    __slots__ = []

    def parse(self, text, pos=0):
        """Return a parse tree of ``text``.

        Initialize the packrat cache and kick off the first ``match()`` call.

        """
        # The packrat cache. {(oid, pos): [length matched at text index 0,
        #                                  length matched at text index 1, ...],
        #                     ...}
        cache = {}

        return self.match(text, pos, cache)
        # TODO: Freak out if the text didn't parse completely: if we didn't get
        # all the way to the end.

    # TODO: Make match() return a bit of the parse tree that the caller can
    # stitch together.
    def match(self, text, pos=0, cache=dummy_cache):
        """Return length of match, ``None`` if no match.

        Check the cache first.

        The default args are just to make the tests easier to write.
        Ordinarily, ``parse()`` calls this and passes in a cache and pos.

        """
        # TODO: Optimize. Probably a hot spot.
        #
        # Is there a way of looking up cached stuff that's faster than hashing
        # this id-pos pair?
        #
        # If this is slow, think about the array module. It might (or might
        # not!) use more RAM, but it'll likely be faster than hashing things
        # all the time. Also, can we move all the allocs up front?
        #
        # To save space, we have lots of choices: (1) Cache only the results of
        # entire rules, not subexpressions. (2) Age stuff out of the cache
        # somehow. LRU?
        expr_id = id(self)
        cached = cache.get((expr_id, pos), ())
        if cached is not ():
            return cached
        match = self._match(text, pos, cache)
        cache[(expr_id, pos)] = match
        return match


class Literal(Expression):
    """A string literal

    Use these if you can; they're the fastest.

    """
    __slots__ = ['literal']

    def __init__(self, literal):
        self.literal = literal

    def _match(self, text, pos=0, cache=dummy_cache):
        if text.startswith(self.literal, pos):
            return len(self.literal)


class Regex(Expression):
    """An expression that matches what a regex does.

    Use these as much as you can and jam as much into each one as you can;
    they're fast.

    """
    __slots__ = ['re']

    def __init__(self, pattern, ignore_case=False, locale=False, multiline=False,
                 dot_all=False, unicode=False, verbose=False):
        self.re = re.compile(pattern, (ignore_case and re.I) |
                                      (locale and re.L) |
                                      (multiline and re.M) |
                                      (dot_all and re.S) |
                                      (unicode and re.U) |
                                      (verbose and re.X))

    def _match(self, text, pos=0, cache=dummy_cache):
        """Return length of match, ``None`` if no match."""
        m = self.re.match(text, pos)
        if m is not None:
            span = m.span()
            return span[1] - span[0]


class _Compound(Expression):
    """An abstract expression which contains other expressions"""

    __slots__ = ['members']

    def __init__(self, *members):
        """``members`` is a sequence of expressions."""
        self.members = members


class Sequence(_Compound):
    """A series of expressions that must match contiguous, ordered pieces of the text

    In other words, it's a concatenation operator: each piece has to match, one
    after another.

    """
    def _match(self, text, pos=0, cache=dummy_cache):
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


class OneOf(_Compound):
    """A series of expressions, one of which must match

    Expressions are tested in order from first to last. The first to succeed
    wins.

    """
    def _match(self, text, pos=0, cache=dummy_cache):
        for m in self.members:
            length = m.match(text, pos, cache)
            if length is not None:
                return length


class AllOf(_Compound):
    """A series of expressions, each of which must succeed from the current position.

    The returned length of the whole expression is the length of the last
    member.

    """
    def _match(self, text, pos=0, cache=dummy_cache):
        for m in self.members:
            length = m.match(text, pos, cache)
            if length is None:
                return None
        return length


class _Container(Expression):
    """An abstract expression that contains a single other expression"""

    __slots__ = ['member']

    def __init__(self, member):
        self.member = member


class Not(_Container):
    """An expression that succeeds only if the expression within it doesn't

    In any case, it never matches any characters.

    """
    def _match(self, text, pos=0, cache=dummy_cache):
        # FWIW, the implementation in Parsing Techniques in Figure 15.29 does
        # not bother to cache NOTs directly.
        length = self.member.match(text, pos, cache)
        return 0 if length is None else None


# Quantifiers. None of these is strictly necessary, but they're darn handy.

class Optional(_Container):
    """An expression that succeeds whether or not the contained one does

    If the contained expression succeeds, it goes ahead and consumes what it
    consumes. Otherwise, it consumes nothing.

    """
    def _match(self, text, pos=0, cache=dummy_cache):
        length = self.member.match(text, pos, cache)
        return 0 if length is None else length


class ZeroOrMore(_Container):
    """An expression wrapper like the * quantifier in regexes."""
    def _match(self, text, pos=0, cache=dummy_cache):
        new_pos = pos
        total_length = 0
        while True:
            length = self.member.match(text, new_pos, cache)
            if not length:  # None or 0. 0 would otherwise loop infinitely.
                return total_length
            new_pos += length
            total_length += length


class OneOrMore(_Container):
    """An expression wrapper like the + quantifier in regexes.

    You can also pass in an alternate minimum to make this behave like "2 or
    more", "3 or more", etc.

    """
    __slots__ = ['min']

    # TODO: Add max. It should probably succeed if there are more than the max
    # --just not consume them.

    def __init__(self, member, min=1):
        super(OneOrMore, self).__init__(member)
        self.min = min

    def _match(self, text, pos=0, cache=dummy_cache):
        new_pos = pos
        total_length = count = 0
        while True:
            length = self.member.match(text, new_pos, cache)
            if length is None:
                break
            count += 1
            if length == 0:  # Don't loop infinitely.
                break
            new_pos += length
            total_length += length
        return total_length if self.min <= count else None