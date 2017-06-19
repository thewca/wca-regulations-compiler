'''
WCAParser : turns an input string into an AST representing the
(translated) Regulations or Guidelines.
'''
import ply.yacc as yacc
from wrc.parse.lexer import WCALexer
from wrc.sema.ast import WCAGuidelines, WCARegulations, WCAStates, Section,\
                         Subsection, TableOfContent, Regulation, Guideline,\
                         Article, LabelDecl, StatesList, State
from wrc.sema.check import HierarchyCheck, LabelCheck

class WCAParser(object):
    ''' Main parser class. Uses WCALexer and yacc to build the AST.'''
    def __init__(self):
        self.lexer = WCALexer().lex()
        self.tokens = WCALexer.tokens
        self.parser = yacc.yacc(module=self, debug=0, write_tables=0)
        self.doctype = WCARegulations
        self.errors = []
        self.warnings = []
        self.sema = {WCAStates : [],
                     WCARegulations : [HierarchyCheck],
                     WCAGuidelines : [HierarchyCheck, LabelCheck]}
        self.toc = None

        # Rules hierarchy related variables
        self.prev_indent = 0
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
        self.current_rule = [None]


    def parse(self, data, doctype):
        '''
        Parse an input string, and return an AST
        doctype must have WCADocument as a baseclass
        '''
        self.doctype = doctype
        self.lexer.lineno = 0
        del self.errors[:]
        del self.warnings[:]
        self.lexer.lexerror = False
        ast = self.parser.parse(data, lexer=self.lexer)
        if self.lexer.lexerror:
            ast = None
        if ast is None:
            self.errors.append("Couldn't build AST.")
        else:
            for check in self.sema[self.doctype]:
                visitor = check()
                if not visitor.visit(ast):
                    self.errors.append("Couldn't visit AST.")
                self.errors.extend(visitor.errors)
                self.warnings.extend(visitor.warnings)
        return (ast, list(self.errors), list(self.warnings))

    def _act_on_list(self, lhs):
        '''
        Act on the following rule :
            items : items item
                  | item
        '''
        lhs[0] = []
        if len(lhs) == 3:
            lhs[0] = lhs[1]
        # lhs[len(lhs)-1] may be different from lhs[-1]
        # Yacc use some internal method to get the element, see yacc.py:240
        item = lhs[len(lhs) - 1]
        if item:
            lhs[0].append(item)

    def p_content(self, content):
        '''content : TITLE opttexts VERSION opttexts sections
                   | TITLE STATESTAG VERSION opttexts states_sections'''
        content[0] = self.doctype(content[1], content[3], content[4], content[5])
        if self.toc:
            self.toc.set_articles([a for a in content[0].sections if isinstance(a, Article)])

    def p_texts(self, texts):
        '''texts : textlist'''
        # We want to merge back the text that we had to split in lexer
        # One \n means linebreak, \n\n changes paragraph
        texts[0] = u"\n".join(texts[1])

    def p_textlist(self, textlist):
        '''textlist : textlist text
                    | text'''
        self._act_on_list(textlist)

    def p_text(self, text):
        '''text : TEXT PARBREAK
                | TEXT
                | PARBREAK'''
        item = text[1]
        text[0] = item if item[0] != "\n" else u""
        if len(text) > 2:
            text[0] += "\n"

    def p_states_sections(self, sections):
        '''states_sections : states_sections states_section
                           | states_section'''
        self._act_on_list(sections)

    def p_states_section(self, body):
        '''states_section : regularsec
                          | states_body'''
        body[0] = body[1]

    def p_states_body(self, section):
        '''states_body : STATESHEADER states'''
        section[0] = StatesList(section[1], section[2])

    def p_sections(self, sections):
        '''sections : sections section
                    | section'''
        self._act_on_list(sections)

    def p_section(self, section):
        '''section : toc
                   | article
                   | regularsec'''
        section[0] = section[1]

    def p_toc(self, toc):
        '''toc : HEADERSEC opttexts TOC opttexts'''
        toc[0] = TableOfContent(toc[1], toc[2], [])
        self.toc = toc[0]

    def p_toc_or_regular_error(self, toc):
        '''toc : HEADERSEC error'''
        # The p_error function just added a generic error, complete it with
        # a more precise one
        self.errors[-1] += ", expected text, subsections or TOC."

    def p_article(self, article):
        '''article : ARTICLEHEADER opttexts rules opttexts'''
        article[0] = Article(article[1][4], article[2], article[3], article[1][0],
                             article[1][1], article[1][2], article[1][3], article[1][5])

    def p_article_error(self, article):
        '''article : ARTICLEHEADER error'''
        # The p_error function just added a generic error, complete it with
        # a more precise one
        self.errors[-1] += ", expected rules or optional texts."

    def p_regularsec(self, regularsec):
        '''regularsec : HEADERSEC opttexts optsubsections'''
        texts = []
        sections = regularsec[2]
        if len(regularsec) > 3:
            texts = regularsec[2]
            sections = regularsec[3]
        regularsec[0] = Section(regularsec[1], texts, sections)

    def p_optsubsections(self, optsubsections):
        '''optsubsections : subsections
                          | '''
        optsubsections[0] = optsubsections[1] if len(optsubsections) > 1 else u""

    def p_opttexts(self, opttexts):
        '''opttexts : texts
                    | '''
        opttexts[0] = opttexts[1] if len(opttexts) > 1 else u""


    def p_subsections(self, subsections):
        '''subsections : subsections subsection
                       | subsection'''
        self._act_on_list(subsections)

    def p_subsection(self, subsection):
        '''subsection : HEADERSUBSEC texts
                      | HEADERSUBSEC texts labeldecls opttexts'''
        content = subsection[3] if len(subsection) > 3 else []
        subsection[0] = Subsection(subsection[1], subsection[2], content)

    def p_labeldecls(self, labeldecls):
        '''labeldecls : labeldecls labeldecl
                      | labeldecl'''
        self._act_on_list(labeldecls)

    def p_labeldecl(self, labeldecl):
        '''labeldecl : LABELDECL'''
        labeldecl[0] = LabelDecl(labeldecl[1][0], labeldecl[1][1])

    def p_rules(self, rules):
        '''rules : rules rule
                 | rule'''
        self._act_on_list(rules)

    def p_rule(self, rule):
        '''rule : GUIDELINE
                | REGULATION'''
        if len(rule[1]) == 4:
            # This is a guideline
            rule[0] = Guideline(rule[1][1], rule[1][2], rule[1][3])
        else:
            # This is a regulation
            indentsize = rule[1][0]
            number = rule[1][1]
            text = rule[1][2]
            parent = None

            # If we just "un"nested, shrink the current rule to our level
            if self.prev_indent > indentsize:
                self.current_rule = self.current_rule[0:indentsize+1]

            # We just added a nested level, the parent is the list's last elem
            if self.prev_indent < indentsize:
                parent = self.current_rule[-1]
            # Else, if we are nested the parent is the one before the last elem
            elif len(self.current_rule) > 1:
                parent = self.current_rule[-2]
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
            if self.prev_indent >= indentsize:
                self.current_rule.pop()
            self.current_rule.append(reg)
            self.prev_indent = indentsize

    def p_states(self, states):
        '''states : states state
                  | state'''
        self._act_on_list(states)

    def p_state(self, state):
        '''state : STATE opttexts'''
        state[0] = State(state[1][0], state[1][1], state[1][2], state[1][3], state[2])

    def p_error(self, elem):
        '''Handle syntax error'''
        self.errors.append("Syntax error on line " + str(self.lexer.lineno)
                           + ". Got unexpected token " + elem.type)
