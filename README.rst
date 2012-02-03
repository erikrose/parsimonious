============
Parsimonious
============

Parsimonious is the fastest PEG parser I could write in pure Python. It was
designed to undergird a MediaWiki parser that wouldn't take 5 seconds or a GB
of RAM to do one page.

Beyond speed, secondary goals include...

* Frugal RAM use
* Minimalistic, understandable code
* Readable grammars
* Extensible grammars
* Complete test coverage

Nice to have are...

* Good error messages


A Little About PEG Parsers
==========================

PEG parsers don't draw a distinction between lexing and parsing; everything's
done at once. As a result, there is no lookahead limit, as there is with, for
instance, Yacc. And, due to both of these properties, PEG grammars are easier
to write: they're basically just EBNF.


Optimizing Grammars
===================

Don't repeat expressions. If you need a ``Regex('such-and-such')`` at some
point in your grammar, don't type it twice; make it a rule of its own, and
reference it from wherever you need it. You'll get the most out of the caching
this way, since cache lookups are by expression object identity (for speed).
Even if you have an expression that's very simple, not repeating it will save
RAM, as there can, at worst, be a cached int for every char in the text you're
parsing.

How much should you shove into one ``Regex``, versus how much should you break
them up to not repeat yourself? That's a fine balance and worthy of
benchmarking. More stuff jammed into a regex will execute faster, because it
doesn't have to run any Python between pieces, but a broken up one will give
better cache performance if the individual pieces are re-used elsewhere. If the
pieces of a regex aren't used anywhere else, by all means keep the whole thing
together.
