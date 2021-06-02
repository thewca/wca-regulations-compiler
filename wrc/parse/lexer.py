'''
WCALexer : tokenize a string using lex.
'''
import re
import ply.lex as lex
from unidecode import unidecode


class WCALexer(object):

    # Token names in the Regulations and Guidelines
    tokens = (
        'TITLE',
        'VERSION',
        'STATESTAG',
        'TOC',
        'LABELDECL',
        'ARTICLEHEADER',
        'STATESHEADER',
        'HEADERSEC',
        'HEADERSUBSEC',
        'TEXT',
        'PARBREAK',
        'REGULATION',
        'GUIDELINE',
        'STATE',
        )


    t_ignore = '\t'

    def t_TITLE(self, token):
        r'\#\s+<wca-title>(?P<title>.+)\n'
        token.value = token.lexer.lexmatch.group("title")
        token.lexer.lineno += 1
        return token

    def t_VERSION(self, token):
        r'<version>(?P<version>.+)\n'
        token.lexer.lineno += 1
        token.value = token.lexer.lexmatch.group("version")
        return token

    def t_STATESTAG(self, token):
        r'<wca-states>\n'
        token.lexer.lineno += 1
        token.value = None
        return token

    def t_TOC(self, token):
        r'<table-of-contents>'
        token.value = token.value
        return token

    def t_LABELDECL(self, token):
        r'-\s<label>\s*\[(?P<label>.+?)\]\s*(?P<text>.+?)\n'
        label = token.lexer.lexmatch.group("label")
        text = token.lexer.lexmatch.group("text")
        token.value = (label, text)
        token.lexer.lineno += 1
        return token

    def t_ARTICLEHEADER(self, token):
        # In the "sep" group, there is a distinct difference between `:` (ASCII colon) and `：` (CJK full-width colon)
        r'\#\#\s+<article-(?P<number>[A-Z0-9]+)><(?P<newtag>[a-zA-Z0-9-]+)><(?P<oldtag>[a-zA-Z0-9-]+)>[ ]*(?P<name>[^\<]+?)(?P<sep>:\s|：)(?P<title>[^<\n]+)\n'
        number = token.lexer.lexmatch.group("number")
        newtag = token.lexer.lexmatch.group("newtag")
        oldtag = token.lexer.lexmatch.group("oldtag")
        name = token.lexer.lexmatch.group("name")
        sep = token.lexer.lexmatch.group("sep")
        title = token.lexer.lexmatch.group("title")
        token.value = (number, newtag, oldtag, name, title, sep)
        token.lexer.lineno += 1
        return token

    def t_STATESHEADER(self, token):
        r'\#\#\s+<states-list>(?P<title>[^<\n]*)\n'
        title = token.lexer.lexmatch.group("title")
        token.value = title
        token.lexer.lineno += 1
        return token

    def t_HEADERSEC(self, token):
        r'\#\#\s+(?P<title>.+?)\n'
        title = token.lexer.lexmatch.group("title")
        token.value = title
        token.lexer.lineno += 1
        return token

    # This is not very flexible, but make the yacc very straightforward
    def t_HEADERSUBSEC(self, token):
        r'\#\#\#\s+(?P<title>.+?)\n'
        title = token.lexer.lexmatch.group("title")
        token.value = title
        token.lexer.lineno += 1
        return token

    def t_REGULATION(self, token):
        r'(?P<indents>\s{4,})*-\s(?P<reg>[a-zA-Z0-9]+)\)\s*(?P<text>.+?[^ ])\n'
        indents = token.lexer.lexmatch.group("indents")
        indents = len(indents)//4 if indents else 0
        reg = token.lexer.lexmatch.group("reg")
        text = token.lexer.lexmatch.group("text")
        token.value = (indents, reg, text)
        token.lexer.lineno += 1
        return token

    def t_GUIDELINE(self, token):
        r'-\s(?P<reg>[a-zA-Z0-9]+[+]+)\)\s\[(?P<label>.+?)\]\s*(?P<text>.+?[^ ])\n'
        reg = token.lexer.lexmatch.group("reg")
        text = token.lexer.lexmatch.group("text")
        label = token.lexer.lexmatch.group("label")
        token.value = (0, reg, text, label)
        token.lexer.lineno += 1
        return token

    def t_STATE(self, token):
        r'-\s\((?P<state>[A-Z]{2}):(?P<continent>[_A-Za-z ]+)(:(?P<friendly_id>[A-Za-z_]+))?\)\s(?P<name>[A-Z].+?[^ ])\n'
        state = token.lexer.lexmatch.group("state")
        continent = token.lexer.lexmatch.group("continent")
        name = token.lexer.lexmatch.group("name")
        friendly_id = token.lexer.lexmatch.group("friendly_id")
        if friendly_id:
            friendly_id = friendly_id
        else:
            friendly_id = unidecode(name).replace("'", "_")
        token.value = (state, continent, name, friendly_id)
        token.lexer.lineno += 1
        return token

    def t_TEXT(self, token):
        r'(?P<text>[^<#\n ].+?[^ ])(?=\n)'
        text = token.lexer.lexmatch.group("text")
        token.value = text
        return token

    def t_PARBREAK(self, token):
        r'\n{2,}'
        token.lexer.lineno += len(token.value)
        return token

    def t_trailingwhitespace(self, token):
        r'.+? \n'
        print("Error: trailing whitespace at line %s in text '%s'" % (token.lexer.lineno + 1, token.value[:-1]))
        token.lexer.lexerror = True
        token.lexer.skip(1)

    def t_newline(self, token):
        r'\n+'
        token.lexer.lineno += len(token.value)

    def t_error(self, token):
        print("Illegal character '%s' at line %s" % (token.value[0], token.lexer.lineno))
        token.lexer.lexerror = True
        token.lexer.skip(1)

    def lex(self):
        return lex.lex(module=self, reflags=re.UNICODE, debug=0)


