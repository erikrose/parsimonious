============
Parsimonious
============

**Parsimonious aims to be the fastest arbitrary-lookahead parser written in pure
Python.** It's based on parsing expression grammars (PEGs), which means you feed 
it a simplified sort of EBNF notation. Parsimonious was designed to undergird a 
MediaWiki parser that wouldn't take 5 seconds or a GB of RAM to do one page.


Goals
=====

* **Speed**
* **Frugal RAM use**
* **Minimalistic, understandable, idiomatic Python code**
* **Readable grammars**
* **Extensible grammars**
* **Complete test coverage**
* **Good error reporting:** I want the parser to work *with* me as I develop a
  grammar.
* **Separation of concerns:** Some Python parsing kits mix recognition with
  instructions about how to turn the resulting tree into some kind of other
  representation. This is limiting when you want to do several different things
  with a tree (for example, render wiki markup to HTML *or* to text).


Example Usage
=============

Here's how to build a simple grammar::

    >>> from parsimonious.grammar import Grammar
    >>> grammar = Grammar(
    ...     """
    ...     bold_text  = bold_open text bold_close
    ...     text       = ~"[A-Z 0-9]*"i
    ...     bold_open  = "(("
    ...     bold_close = "))"
    ...     """)

You can have forward references and even right recursion. It's all taken care
of by the grammar compiler. The first rule is taken to be the default start 
symbol, but may be overridden.

Next, let's parse something and get an abstract syntax tree::

    >>> grammar.parse('((bold stuff))')
    <Node called "bold_text" matching "((bold stuff))">
        <Node called "bold_open" matching "((">
        <RegexNode called "text" matching "bold stuff">
        <Node called "bold_close" matching "))">

You'd typically then use a ``nodes.NodeVisitor`` subclass (see below) to walk
the tree and do something useful with it.


Current Status
==============

* ``0.3`` is a pretty usable release for inputs that aren't huge. I haven't 
  really started optimizing yet. 
* Everything that exists works. Test coverage is good.
* There may be API changes until we get to ``1.0``.
* I don't plan on making any backward-incompatible changes to the rule syntax
  in the future, so you can write grammars without fear.
* It may be slow and use a lot of RAM; I haven't measured either yet. However,
  I have several macro- and micro-optimizations in mind.
* Error reporting is fairly uninformative, and debugging is nonexistent.
  However, ``repr`` methods of expressions, grammars, and nodes are very clear
  and helpful. Ones of ``Grammar`` objects are even round-trippable! Huge
  things are planned for grammar debugging in the future.
* The grammar extensibility story is underdeveloped at the moment. You should
  be able to extend a grammar by simply concatening more rules onto the
  existing ones; later rules of the same name should override previous ones.
  However, this is untested and may not be the final story.
* Sphinx docs are coming, but the docstrings are quite useful now.


Coming up soon...
-----------------

* Optimizations to make Parsimonious worthy of its name
* Tighter RAM use
* Better-thought-out grammar extensibility story


A Little About PEG Parsers
==========================

PEG parsers don't draw a distinction between lexing and parsing. Everything's
done at once. As a result, there's no lookahead limit (for example, as with 
YACC). And, due to both of these properties, PEG grammars are easier to 
write: they're basically just a more practical dialect of EBNF. 

With caching, they take ``O(grammar size × text length)`` memory (though I plan 
to do better), but they run in ``O(text length)`` time.


More Technically
----------------

PEGs can describe a superset of *LL(k)* languages, any deterministic *LR(k)*
language, and many others—including some that aren't context-free
(http://www.brynosaurus.com/pub/lang/peg.pdf). They can also deal with what
would be ambiguous languages if described in canonical EBNF. They do this by
trading the ``|`` alternation operator for the ``/`` operator, which works the
same except that it makes priority explicit: ``a / b / c`` first tries matching
``a``. If that fails, it tries ``b``, and, failing that, moves on to ``c``.
Thus, ambiguity is resolved by always yielding the first successful recognition.


Writing Grammars
================

Grammars are defined by a series of rules, one per line. The syntax should be
familiar to anyone who uses regexes or reads programming language manuals. An
example will serve best::

    styled_text = bold_text / italic_text
    bold_text   = "((" text "))"
    italic_text = "''" text "''"
    text        = ~"[A-Z 0-9]*"i


Syntax Reference
----------------

====================    ========================================================
``"some literal"``      Used to quote literals. Backslash escaping and Python 
                        conventions for "raw" and Unicode strings help support 
                        fiddly characters.

[space]                 Sequences are made out of space- or tab-delimited
                        things. ``a b c`` matches spots where those 3
                        terms appear in that order.

``a / b``               Alternatives. The first to succeed of ``a / b / c`` 
                        wins.

``thing?``              An optional expression. This is greedy, always consuming 
                        ``thing`` if it exists.

``&thing``              A lookahead assertion. Ensures ``thing`` matches at the 
                        current position but does not consume it.

``!thing``              A negative lookahead assertion. Matches if ``thing`` 
                        isn't found here. Doesn't consume any text.

``things*``             Zero or more things. This is greedy, always consuming as
                        many repetitions as it can.

``things+``             One or more things. This is greedy, always consuming as 
                        many repetitions as it can.

``~r"regex"ilmsux``     Regexes have ``~`` in front and are quoted like
                        literals. Any flags follow the end quotes as single
                        chars. Regexes are good for representing character
                        classes (``[a-z0-9]``) and optimizing for speed. The
                        downside is that they won't be able to take advantage
                        of our fancy debugging, once we get that working.
                        Ultimately, I'd like to deprecate explicit regexes and
                        instead have Parsimonious dynamically build them out of
                        simpler primitives.
====================    ========================================================


Optimizing Grammars
===================

Don't repeat expressions 
------------------------

If you need a ``~"[a-z0-9]"i`` at two points in your grammar, don't type it 
twice. Make it a rule of its own, and reference it from wherever you need it. 
You'll get the most out of the caching this way, since cache lookups are by 
expression object identity (for speed). 

Even if you have an expression that's very simple, not repeating it will 
save RAM, as there can, at worst, be a cached int for every char in the text 
you're parsing. In the future, we may identify repeated subexpressions 
automatically and factor them up while building the grammar.

How much should you shove into one regex, versus how much should you break them
up to not repeat yourself? That's a fine balance, and worthy of benchmarking.
More stuff jammed into a regex will execute faster, because it doesn't have to
run any Python between pieces; but a broken-up one will give better cache
performance if the individual pieces are re-used elsewhere. If the pieces of a
regex aren't used anywhere else, by all means keep the whole thing together.


Quantifiers
-----------

Bring your ``?`` and ``*`` quantifiers up to the highest level you
can. Otherwise, lower-level patterns could succeed but be empty and put a bunch
of useless nodes in your tree that didn't really match anything.


Processing Parse Trees
======================

A parse tree has a node for each expression matched, even if it matched a
zero-length string, like ``"thing"?`` might.

The ``NodeVisitor`` class provides an inversion-of-control framework for
walking a tree, and returning a new construct (tree/string/whatever) based
on it. For now, have a look at its docstrings for more detail. There's also a
good example in ``grammar.RuleVisitor``. Notice how we take advantage of nodes'
iterability by using tuple unpacks in the formal parameter lists::

    def visit_or_term(self, or_term, (_, slash, term)):
        ...

When something goes wrong in your visitor, you get a nice error like this::

    [normal traceback here...]
    VisitationException: 'Node' object has no attribute 'foo'

    Parse tree:
    <Node called "rules" matching "number = ~"[0-9]+"">  <-- *** We were here. ***
        <Node matching "number = ~"[0-9]+"">
            <Node called "rule" matching "number = ~"[0-9]+"">
                <Node matching "">
                <Node called "label" matching "number">
                <Node matching " ">
                    <Node called "_" matching " ">
                <Node matching "=">
                <Node matching " ">
                    <Node called "_" matching " ">
                <Node called "rhs" matching "~"[0-9]+"">
                    <Node called "term" matching "~"[0-9]+"">
                        <Node called "atom" matching "~"[0-9]+"">
                            <Node called "regex" matching "~"[0-9]+"">
                                <Node matching "~">
                                <Node called "literal" matching ""[0-9]+"">
                                <Node matching "">
                <Node matching "">
                <Node called "eol" matching "
                ">
        <Node matching "">

The parse tree is tacked onto the exception, and the node whose visitor method
raised the error is pointed out.


Why No Streaming Tree Processing?
---------------------------------

Some have asked why we don't process the tree as we go (SAX-style). There are
two main reasons:

1. It wouldn't work. With a PEG parser, no parsing decision is final until the
   whole text is parsed. If we had to change a decision, we'd have to backtrack
   and redo the SAX-style interpretation as well, which would involve
   reconstituting part of the AST and quite possibly scuttling whatever you
   were doing with the streaming output. (Note that some bursty SAX-style
   processing may be possible in the future if we use cuts.)

2. It interferes with the ability to derive multiple representations from the
   AST. For example: first HTML, and then text (from wiki markup).


Future Directions
=================


Rule Syntax Changes
-------------------

* Maybe support left-recursive rules like PyMeta, if anybody cares.
* Ultimately, I'd like to get rid of explicit regexes, and break them into more
  atomic things like character classes. Then we can dynamically compile bits
  of the grammar into regexes as necessary to boost speed.


Optimizations
-------------

* Make RAM use almost constant by automatically inserting "cuts", as described
  in
  http://ialab.cs.tsukuba.ac.jp/~mizusima/publications/paste513-mizushima.pdf.
  This would also improve error reporting, as we wouldn't backtrack out of
  everything informative before finally failing.
* Find all the distinct subexpressions, and unify duplicates for a better cache
  hit ratio.
* Think about having the user (optionally) provide some representative input
  along with a grammar. We can then profile against it, see which expressions
  are worth caching, and annotate the grammar. Perhaps there will even be
  positions at which a given expression is more worth caching. Or we could keep
  a count of how many times each cache entry has been used and evict the most
  useless ones as RAM use grows.
* We could possibly compile the grammar into VM instructions, like in "A
  parsing machine for PEGs" by Medeiros.
* If recursion gets too deep in practice, use trampolining to dodge it.
* It looks like we could make an architecture-independent ``.o`` file and use LLVM
  to JIT it to whatever arch we're on: https://github.com/dabeaz/bitey/. Of
  course, then everybody has to have LLVM, which is even harder to set up than
  a vanilla C toolchain.


Niceties
--------

* Pijnu has a raft of tree manipulators. I don't think I want all of them, but
  a judicious subset might be nice. Don't get into mixing formatting with tree
  manipulation.
  https://github.com/erikrose/pijnu/blob/master/library/node.py#L333. PyPy's
  parsing lib exposes a sane subset:
  http://doc.pypy.org/en/latest/rlib.html#tree-transformations.


Version History
===============

0.3
  * Support comments, the ``!`` ("not") operator, and parentheses in grammar
    definition syntax.
  * Change the ``&`` operator to a prefix operator to conform to the original
    PEG syntax. The version in Parsing Techniques was infix, and that's what I
    used as a reference. However, the unary version is more convenient, as it
    lets you spell ``AB & A`` as simply ``A &B``.
  * Take the ``print`` statements out of the benchmark tests.
  * Give Node an evaluate-able ``__repr__``.

0.2
  * Support matching of prefixes and other not-to-the-end slices of strings by
    making ``match()`` public and able to initialize a new cache. Add
    ``match()`` callthrough method to ``Grammar``.
  * Report a ``BadGrammar`` exception (rather than crashing) when there are
    mistakes in a grammar definition.
  * Simplify grammar compilation internals: get rid of superfluous visitor
    methods and factor up repetitive ones. Simplify rule grammar as well.
  * Add ``NodeVisitor.lift_child`` convenience method.
  * Rename ``VisitationException`` to ``VisitationError`` for consistency with
    the standard Python exception hierarchy.
  * Rework ``repr`` and ``str`` values for grammars and expressions. Now they
    both look like rule syntax. Grammars are even round-trippable! This fixes a
    unicode encoding error when printing nodes that had parsed unicode text.
  * Add tox for testing. Stop advertising Python 2.5 support, which never
    worked (and won't unless somebody cares a lot, since it makes Python 3
    support harder).
  * Settle (hopefully) on the term "rule" to mean "the string representation of
    a production". Get rid of the vague, mysterious "DSL".

0.1
  * A rough-but-useable preview release
