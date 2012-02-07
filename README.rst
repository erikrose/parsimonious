============
Parsimonious
============

Parsimonious aims to be the fastest PEG parser written in pure Python. It was
designed to undergird a MediaWiki parser that wouldn't take 5 seconds or a GB
of RAM to do one page.

Beyond speed, secondary goals include...

* Frugal RAM use
* Minimalistic, understandable code
* Readable grammars
* Extensible grammars
* Complete test coverage
* Separation of concerns. Some Python parsing kits mix recognition with
  instructions about how to transform the resulting tree. It felt unnatural to
  me, since my use case--wikis--naturally wants to do several different things
  with the tree: render to HTML, render to text, etc.
* Good error messages. I want the parser to work *with* me as I develop a
  grammar.


A Little About PEG Parsers
==========================

PEG parsers don't draw a distinction between lexing and parsing; everything's
done at once. As a result, there is no lookahead limit, as there is with, for
instance, Yacc. And, due to both of these properties, PEG grammars are easier
to write: they're basically just EBNF. With caching, they take O(grammar size *
text length) memory, but they run in O(text length) time.


Writing Grammars
================

* Literals are quoted with ``"`` and support backslash escaping and Python
  conventions for "raw" and Unicode strings.
* Sequences are made out of space- or tab-delimited things.
* OneOf choices have ``/`` between them.
* AllOf components have ``&`` between them.
* Optional has ``?`` after it.
* Not has ``!`` before it.
* ZeroOrMore has ``*`` after it.
* OneOrMore has ``+`` after it.
* I shouldn't need to represent Empty; the quantifiers should suffice.
* Nonterminals just sit out there naked. Valid names are
  ``[a-zA-Z_][a-zA-Z_0-9]*``.
* Regexes have ``~`` in front and are quoted like literals. Any flags follow
  the end quotes as single chars.

Example::

    bold_text  = bold_open text bold_close
    text       = ~"[A-Z 0-9]*"i
    bold_open  = '(('
    bold_close = '))'

We might implement parentheses in the future for anonymous grouping. For now,
just break up complex rules instead.

Wishes:

* The ability to mark certain nodes as undesired, so we don't bother
  constructing them and cluttering the tree with them. For example, we might
  only care to see the OneOf node in the final tree, not the boring Literals
  inside it::

    greeting = hi / hello / bonjour

  Perhaps we could express it like this::

    greeting = -hi / -hello / -bonjour

  Pijnu has a raft of tree manipulators. I don't think I want all of them, but
  a judicious subset might be nice. Don't get into mixing formatting with tree
  manipulation.
  https://github.com/erikrose/pijnu/blob/master/library/node.py#L333
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
doesn't have to run any Python between pieces, but a broken-up one will give
better cache performance if the individual pieces are re-used elsewhere. If the
pieces of a regex aren't used anywhere else, by all means keep the whole thing
together.

Quantifiers: bring your ``?`` and ``*`` quantifiers up to the highest level you
can. Otherwise, lower-level patterns could succeed but be empty and put a bunch
of useless nodes in your tree that didn't really match anything.


Dealing With Parse Trees
========================

A parse tree has a node for each expression matched, even if it matched a
zero-length string, like ``"thing"?`` might do.

TODO: Talk about tree manipulators (if we write any) and about ``NodeVisitor``.

When something goes wrong in your visitor, you get a nice error like this::

    VisitationException: 'Node' object has no attribute 'name'

    Parse tree:
    <rules "number = ~"[0-9]+"">  <-- *** We were here. ***
        <Node "number = ~"[0-9]+"">
            <rule "number = ~"[0-9]+"">
                <Node "">
                <label "number">
                <Node " ">
                    <_ " ">
                <Node "=">
                <Node " ">
                    <_ " ">
                <rhs "~"[0-9]+"">
                    <term "~"[0-9]+"">
                        <atom "~"[0-9]+"">
                            <regex "~"[0-9]+"">
                                <Node "~">
                                <literal ""[0-9]+"">
                                <Node "">
                <Node "">
                <eol "
                ">
        <Node "">

Note the parse tree tacked onto the exception. The node whose visitor method
raised the error is pointed out.


Why?
====

* Speed
* I wanted to understand PEG parsers better so I'd know how to optimize my grammars.
