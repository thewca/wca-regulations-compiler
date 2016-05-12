'''
WCAParser : turns an input string into an AST representing the
(translated) Regulations or Guidelines.
'''
import ply.yacc as yacc
from parse.lexer import WCALexer
from sema.ast import WCAGuidelines, WCARegulations, Section, Subsection,\
                     TableOfContent, Regulation, Guideline, Article, LabelDecl
from sema.check import HierarchyCheck, LabelCheck

class WCAParser(object):
    ''' Main parser class. Uses WCALexer and yacc to build the AST.'''
    def __init__(self):
        self.lexer = WCALexer().lex()
        self.tokens = WCALexer.tokens
        self.parser = yacc.yacc(module=self, debug=0)
        self.doctype = WCARegulations
        self.errors = []
        self.warnings = []
        self.sema = { WCARegulations : [HierarchyCheck],
                      WCAGuidelines : [HierarchyCheck, LabelCheck]
                    }
        self.toc = None

        # Rules hierarchy related variables
        self.prevIndent = 0
        # Contains the hierarchy at the current level, to be able to
        # know one rule's parent rule
        # Example :
        # 1 before: (None), after: (1)
        #   1.1 before: (1), after: (1, 1.1)
        #     1.1.a before: (1, 1.1), after: (1, 1.1, 1.1.a)
        #   1.2 before: (1, 1.1, 1.1.a), after: (1, 1.2)
        # 2 before: (1, 1.2), after: (2)
        # Note: it does *not* check hierarchy, ie "3.2" could be nested in "1"
        # The Sema HierarchyCheck checks this
        self.currentRule = [None]


    def parse(self, data, doctype):
        '''
        Parse an input string, and return an AST
        doctype must have WCADocument as a baseclass
        '''
        self.doctype = doctype
        ast = self.parser.parse(data, lexer=self.lexer)
        if ast is None:
            self.errors.append("Couldn't build AST.")
        else:
            for check in self.sema[self.doctype]:
                visitor = check()
                if not visitor.visit(ast):
                    self.errors.append("Couldn't visit AST.")
                self.errors.extend(visitor.errors)
                self.warnings.extend(visitor.warnings)
        return (ast, self.errors, self.warnings)

    def _act_on_list(self, lhs):
        '''
        Act on the following rule :
            items : items item
                  | item
        '''
        lhs[0] = []
        if len(lhs) == 3:
            lhs[0] = lhs[1]
        # For some reason here lhs[len(lhs)-1] may be different from lhs[-1]
        item = lhs[len(lhs) - 1]
        if item:
            lhs[0].append(item)

    def p_content(self, content):
        '''content : title version sections'''
        content[0] = self.doctype(content[1], content[2], content[3])
        self.toc.set_articles([a for a in content[0].sections if isinstance(a, Article)])

    def p_title(self, title):
        '''title : H1 TITLE STRING'''
        title[0] = title[3]

    def p_version(self, version):
        '''version : VERSION STRING'''
        version[0] = version[2]

    def p_sections(self, sections):
        '''sections : sections section
                    | section'''
        self._act_on_list(sections)

    def p_section(self, section):
        '''section : h2 sectionintro sectioncontent'''
        if isinstance(section[1], tuple):
            section[0] = Article(section[1][3], section[2], section[3], section[1][0],
                                 section[1][1], section[1][2])
        elif not isinstance(section[3], list):
            section[0] = TableOfContent(section[1], section[2], [])
            self.toc = section[0]
        else:
            section[0] = Section(section[1], section[2], section[3])

    def p_sectionintro(self, sectionintro):
        '''sectionintro : paragraphs
                        | empty'''
        sectionintro[0] = sectionintro[1]

    def p_sectioncontent(self, sectioncontent):
        '''sectioncontent : rules
                          | subsections
                          | TOC '''
        sectioncontent[0] = sectioncontent[1]

    def p_rules(self, rules):
        '''rules : rules rule
                 | rule'''
        self._act_on_list(rules)

    def p_rule(self, rule):
        '''rule : indents RULENUMBER STRING
                | RULENUMBER STRING
                | GUIDENUMBER LABEL STRING'''
        if isinstance(rule[1], basestring) and rule[1].endswith('+'):
            rule[0] = Guideline(rule[1], rule[3], rule[2])
        else:
            indentsize = 0
            number = rule[1]
            text = rule[2]
            if isinstance(rule[1], list):
                indentsize = len(rule[1])
                number = rule[2]
                text = rule[3]
            parent = None

            # If we just "un"nested, shrink the current rule to our level
            if self.prevIndent > indentsize:
                self.currentRule = self.currentRule[0:indentsize+1]

            # We just added a nested level, the parent is the list's last elem
            if self.prevIndent < indentsize:
                parent = self.currentRule[-1]
            # Else, if we are nested the parent is the one before the last elem
            elif len(self.currentRule) > 1:
                parent = self.currentRule[-2]
            # Else if we are not nested, then we are a root rule and parent is none
            # (do nothing as parent is initialized to none)

            # Create the regulation node
            reg = Regulation(number, text, parent)

            # Let our parent knows he has a new child, if we don't have a parent
            # let's create an item in the article rules list
            if parent:
                parent.add_child(reg)
            else:
                rule[0] = reg

            # Unless we nested, pop and replace the last rule by ourself
            # If we added a nesting level, we just need to add ourself
            if self.prevIndent >= indentsize:
                self.currentRule.pop()
            self.currentRule.append(reg)
            self.prevIndent = indentsize



    def p_indents(self, indents):
        '''indents : indents INDENT
                   | INDENT'''
        self._act_on_list(indents)

    def p_subsections(self, subsections):
        '''subsections : subsections subsection
                       | subsection'''
        self._act_on_list(subsections)

    def p_subsection(self, subsection):
        '''subsection : H3 STRING paragraphs subsectioncontent'''
        subsection[0] = Subsection(subsection[2], subsection[3], subsection[4])

    def p_subsectioncontent(self, subsectioncontent):
        '''subsectioncontent : labeldecls
                             | empty'''
        subsectioncontent[0] = subsectioncontent[1]

    def p_labeldecls(self, labeldecls):
        '''labeldecls : labeldecls labeldecl
                      | labeldecl'''
        self._act_on_list(labeldecls)

    def p_labeldecl(self, labeldecl):
        '''labeldecl : LABELDECL LABEL STRING'''
        labeldecl[0] = LabelDecl(labeldecl[2], labeldecl[3])

    def p_paragraphs(self, paragraphs):
        '''paragraphs : paragraphs STRING
                      | STRING'''
        self._act_on_list(paragraphs)

    def p_h2(self, header):
        '''h2 : H2 STRING
              | H2 TAG STRING
              | H2 ARTICLENUMBER TAG TAG STRING'''
        if len(header) < 6:
            header[0] = header[len(header) - 1]
        else:
            header[0] = (header[2], header[3], header[4], header[5])

    def p_empty(self, empty):
        '''empty :
                 | SEPARATOR'''
        empty[0] = []

    def p_error(self, elem):
        '''Handle syntax error'''
        print "Syntax error on line " + str(self.lexer.lineno-1)
        print "Unexpected " + elem.type
