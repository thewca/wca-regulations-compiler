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
        ur'\#\s+<wca-title>(?P<title>.+)\n'
        token.value = token.lexer.lexmatch.group("title").decode("utf8")
        token.lexer.lineno += 1
        return token

    def t_VERSION(self, token):
        ur'<version>(?P<version>.+)\n'
        token.lexer.lineno += 1
        token.value = token.lexer.lexmatch.group("version").decode("utf8")
        return token

    def t_STATESTAG(self, token):
        ur'<wca-states>\n'
        token.lexer.lineno += 1
        token.value = None
        return token

    def t_TOC(self, token):
        ur'<table-of-contents>'
        token.value = token.value.decode("utf8")
        return token

    def t_LABELDECL(self, token):
        ur'-\s<label>\s*\[(?P<label>.+?)\]\s*(?P<text>.+?)\n'
        label = token.lexer.lexmatch.group("label").decode("utf8")
        text = token.lexer.lexmatch.group("text").decode("utf8")
        token.value = (label, text)
        token.lexer.lineno += 1
        return token

    def t_ARTICLEHEADER(self, token):
        # \xef\xbc\x9a is the "fullwidth colon" used in Japanese for instance
        ur'\#\#\s+<article-(?P<number>[A-Z0-9]+)><(?P<newtag>[a-zA-Z0-9-]+)><(?P<oldtag>[a-zA-Z0-9-]+)>[ ]*(?P<name>[^\<]+?)(?P<sep>:\s|\xef\xbc\x9a)(?P<title>[^<\n]+)\n'
        number = token.lexer.lexmatch.group("number").decode("utf8")
        newtag = token.lexer.lexmatch.group("newtag").decode("utf8")
        oldtag = token.lexer.lexmatch.group("oldtag").decode("utf8")
        name = token.lexer.lexmatch.group("name").decode("utf8")
        sep = token.lexer.lexmatch.group("sep").decode("utf8")
        title = token.lexer.lexmatch.group("title").decode("utf8")
        token.value = (number, newtag, oldtag, name, title, sep)
        token.lexer.lineno += 1
        return token

    def t_STATESHEADER(self, token):
        ur'\#\#\s+<states-list>(?P<title>[^<\n]+)\n'
        title = token.lexer.lexmatch.group("title").decode("utf8")
        token.value = title
        token.lexer.lineno += 1
        return token

    def t_HEADERSEC(self, token):
        ur'\#\#\s+(?P<title>.+?)\n'
        title = token.lexer.lexmatch.group("title").decode("utf8")
        token.value = title
        token.lexer.lineno += 1
        return token

    # This is not very flexible, but make the yacc very straightforward
    def t_HEADERSUBSEC(self, token):
        ur'\#\#\#\s+(?P<title>.+?)\n'
        title = token.lexer.lexmatch.group("title").decode("utf8")
        token.value = title
        token.lexer.lineno += 1
        return token

    def t_REGULATION(self, token):
        ur'(?P<indents>\s{4,})*-\s(?P<reg>[a-zA-Z0-9]+)\)\s*(?P<text>.+?[^ ])\n'
        indents = token.lexer.lexmatch.group("indents")
        indents = len(indents)/4 if indents else 0
        reg = token.lexer.lexmatch.group("reg").decode("utf8")
        text = token.lexer.lexmatch.group("text").decode("utf8")
        token.value = (indents, reg, text)
        token.lexer.lineno += 1
        return token

    def t_GUIDELINE(self, token):
        ur'-\s(?P<reg>[a-zA-Z0-9]+[+]+)\)\s\[(?P<label>.+?)\]\s*(?P<text>.+?[^ ])\n'
        reg = token.lexer.lexmatch.group("reg").decode("utf8")
        text = token.lexer.lexmatch.group("text").decode("utf8")
        label = token.lexer.lexmatch.group("label").decode("utf8")
        token.value = (0, reg, text, label)
        token.lexer.lineno += 1
        return token

    def t_STATE(self, token):
        ur'-\s\((?P<state>[A-Z]{2}):(?P<continent>[_A-Za-z ]+)(:(?P<friendly_id>[A-Za-z_]+))?\)\s(?P<name>[A-Z].+?[^ ])\n'
        state = token.lexer.lexmatch.group("state").decode("utf8")
        continent = token.lexer.lexmatch.group("continent").decode("utf8")
        name = token.lexer.lexmatch.group("name").decode("utf8")
        friendly_id = token.lexer.lexmatch.group("friendly_id")
        if friendly_id:
            friendly_id = friendly_id.decode("utf8")
        else:
            friendly_id = unidecode(name).replace("'", "_")
        token.value = (state, continent, name, friendly_id)
        token.lexer.lineno += 1
        return token

    def t_TEXT(self, token):
        ur'(?P<text>[^<#\n ].+?[^ ])(?=\n)'
        text = token.lexer.lexmatch.group("text").decode("utf8")
        token.value = text
        return token

    def t_PARBREAK(self, token):
        ur'\n{2,}'
        token.lexer.lineno += len(token.value)
        return token

    def t_trailingwhitespace(self, token):
        ur'.+? \n'
        print "Error: trailing whitespace at line %s in text '%s'" % (token.lexer.lineno + 1, token.value[:-1])
        token.lexer.lexerror = True
        token.lexer.skip(1)

    def t_newline(self, token):
        ur'\n+'
        token.lexer.lineno += len(token.value)

    def t_error(self, token):
        print "Illegal character '%s' at line %s" % (token.value[0], token.lexer.lineno)
        token.lexer.lexerror = True
        token.lexer.skip(1)

    def lex(self):
        return lex.lex(module=self, reflags=re.UNICODE, debug=0)


