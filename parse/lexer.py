'''
WCALexer : tokenize a string using lex.
'''
import ply.lex as lex


class WCALexer(object):

    # Token names in the Regulations and Guidelines
    tokens = (
        'TITLE',
        'VERSION',
        'TOC',
        'H1',
        'H2',
        'H3',
        'LABELDECL',
        'ARTICLENUMBER',
        'TAG',
        'INDENT',
        'RULENUMBER',
        'GUIDENUMBER',
        'LABEL',
        'STRING',
        'SEPARATOR',
        )


    t_H1 = r'\#'
    t_H2 = r'\#\#'
    t_H3 = r'\#\#\#'
    t_ignore = '-\t'

    def t_TITLE(self, token):
        r'<wca-title>'
        return token

    def t_VERSION(self, token):
        r'<version>'
        return token

    def t_TOC(self, token):
        r'<table-of-contents>'
        return token

    def t_LABELDECL(self, token):
        r'<label>'
        return token

    def t_ARTICLENUMBER(self, token):
        r'<article-[A-Z0-9]+>'
        token.value = token.value[9:-1]
        return token

    def t_TAG(self, token):
        r'<[a-zA-Z0-9-]+>'
        # FIXME use named group
        token.value = token.value[1:-1]
        return token

    def t_INDENT(self, token):
        r'[ ]{4}'
        return token

    def t_RULENUMBER(self, token):
        r'([a-zA-Z0-9]+)\)'
        token.value = token.value[:-1]
        return token

    def t_GUIDENUMBER(self, token):
        r'([a-zA-Z0-9]+[+]+)\)'
        token.value = token.value[:-1]
        return token

    def t_LABEL(self, token):
        r'\[[^\]]+\](?!\()'
        # Negative lookahead for a parenthesis (markdown link)
        # FIXME use named group
        token.value = token.value[1:-1]
        return token

    def t_STRING(self, token):
        r'[^-<#\n ].+\n'
        token.value = token.value[:-1]
        token.lexer.lineno += 1
        return token

    def t_SEPARATOR(self, token):
        # ignore
        r'[ ]'

    def t_newline(self, token):
        r'\n+'
        token.lexer.lineno += len(token.value)

    def t_error(self, token):
        print "Illegal character '%s'" % token.value[0]
        token.lexer.skip(1)

    def lex(self):
        return lex.lex(module=self)


