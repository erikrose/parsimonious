"""Parsimonious aims to be the fastest arbitrary-lookahead parser written in 
pure Python. 

It's based on parsing expression grammars (PEGs), which means you feed it a
simplified sort of EBNF notation. Parsimonious was designed to undergird a
MediaWiki parser that wouldn't take 5 seconds or a GB of RAM to do one page.

Goals
-----
* Speed
* Frugal RAM use
* Minimalistic, understandable, idiomatic Python code
* Readable grammars
* Extensible grammars
* Complete test coverage
* Good error reporting
* Separation of concerns

"""
