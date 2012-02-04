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


Writing Grammars
================

* Literals are quoted with ``"`` and support backslash escaping.
* Sequences are made out of space- or tab-delimited things.
* OneOf choices have ``/`` between them.
* AllOf components have ``&`` between them.
* Optional has ``?`` after it.
* Not has ``!`` before it.
* ZeroOrMore has ``*`` after it.
* OneOrMore has ``+`` after it.
* I shouldn't need to represent Empty; the quantifiers should suffice.
* Nonterminals just sit out there naked. Valid names are [a-zA-Z_][a-zA-Z_0-9]*.
* Regexes have ``~`` in front and are quoted like literals. Any flags follow
  the end quotes as single chars. TODO: Think about support Python-style raw
  strings.

Example::

    bold_text  = bold_open text bold_close
    text       = ~'[A-Z 0-9]*'i
    bold_open  = '(('
    bold_close = '))'

What about precedence? Rather than have parens or something, just break up
rules to do grouping.

Wishes:
* The ability to mark certain nodes as undesired, so we don't bother
  constructing them and cluttering the tree with them
* Think about having the ability, like PyParsing, to get irrevocably into a
  pattern so that we don't backtrack out of it. Then, if things don't end up
  matching, we complain with an informative error message rather than
  backtracking to nonsense.


Optimizing Grammars
===================

Don't repeat expressions. If you need a ``Regex('such-and-such')`` at some
point in your grammar, don't type it twice; make it a rule of its own, and
reference it from wherever you need it. You'll get the most out of the caching
this way, since cache lookups are by expression object identity (for speed).
Even if you have an expression that's very simple, not repeating it will save
RAM, as there can, at worst, be a cached int for every char in the text you're
parsing. But hmm, maybe I can identify repeat subexpressions automatically and
factor that up while building the grammar....

How much should you shove into one ``Regex``, versus how much should you break
them up to not repeat yourself? That's a fine balance and worthy of
benchmarking. More stuff jammed into a regex will execute faster, because it
doesn't have to run any Python between pieces, but a broken up one will give
better cache performance if the individual pieces are re-used elsewhere. If the
pieces of a regex aren't used anywhere else, by all means keep the whole thing
together.

Quantifiers: bring your quantifiers up to the topmost level you can. Otherwise,
lower-level patterns could succeed but be empty and put a bunch of useless
nodes in your tree that didn't really match anything.


Why?
====

* Speed
* I wanted to understand PEG parsers better so I'd know how to optimize my grammars.
* I didn't like how PyParsing mixed recognition with formatting the resulting tree. It felt unnatural to me, since my use case--wikis--naturally wants to do several different things with the tree: render to HTML, render to text, etc.
