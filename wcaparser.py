'''
WCAParser : turns an input string into an AST representing the
(translated) Regulations or Guidelines.
'''
import ply.yacc as yacc
from wcalexer import WCALexer

class WCAParser(object):
    ''' Main parser class. Uses WCALexer and yacc to build the AST.'''
    def __init__(self):
        self.lexer = WCALexer().lex()
        self.tokens = WCALexer.tokens
        self.parser = yacc.yacc(module=self)

    def parse(self, data):
        '''Parse an input string, and return an AST'''
        return self.parser.parse(data, lexer=self.lexer)


    def p_content(self, content):
        '''content : title version sections'''

    def p_title(self, title):
        '''title : H1 TITLE STRING'''

    def p_version(self, version):
        '''version : VERSION STRING'''

    def p_sections(self, sections):
        '''sections : sections section
                    | section'''

    def p_section(self, section):
        '''section : h2 sectionintro sectioncontent'''

    def p_sectionintro(self, sectionintro):
        '''sectionintro : paragraphs
                        | empty'''

    def p_sectioncontent(self, sectioncontent):
        '''sectioncontent : rules
                          | subsections
                          | TOC '''

    def p_rules(self, rules):
        '''rules : rules rule
                 | rule'''

    def p_rule(self, rule):
        '''rule : indents RULENUMBER STRING
                | RULENUMBER STRING
                | GUIDENUMBER LABEL STRING'''

    def p_indents(self, indents):
        '''indents : indents INDENT
                   | INDENT'''

    def p_subsections(self, subsections):
        '''subsections : subsections subsection
                       | subsection'''

    def p_subsection(self, subsection):
        '''subsection : H3 STRING paragraphs subsectioncontent'''

    def p_subsectioncontent(self, subsectioncontent):
        '''subsectioncontent : labeldefs
                           | empty'''

    def p_labeldefs(self, labeldefs):
        '''labeldefs : labeldefs labeldef
                     | labeldef'''

    def p_labeldef(self, labeldef):
        '''labeldef : LABELDEF LABEL STRING'''

    def p_paragraphs(self, paragraphs):
        '''paragraphs : paragraphs STRING
                      | STRING'''

    def p_h2(self, header):
        '''h2 : H2 STRING
              | H2 TAG STRING
              | H2 ARTICLENUMBER TAG TAG STRING'''

    def p_empty(self, empty):
        '''empty :
                 | SEPARATOR'''
        pass

    def p_error(self, elem):
        '''Handle syntax error'''
        print "Syntax error on line " + str(self.lexer.lineno-1)
        print "Unexpected " + elem.type
