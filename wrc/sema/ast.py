from functools import total_ordering

class WCADocument(object):
    def __init__(self, title, version, text, sections):
        self.title = title
        self.sections = sections
        self.text = text
        self.version = version

class WCARegulations(WCADocument):
    def __init__(self, title, version, text, sections):
        super(WCARegulations, self).__init__(title, version, text, sections)

class WCAGuidelines(WCADocument):
    def __init__(self, title, version, text, sections):
        super(WCAGuidelines, self).__init__(title, version, text, sections)

class WCAStates(WCADocument):
    def __init__(self, title, version, text, sections):
        super(WCAStates, self).__init__(title, version, text, sections)

class Section(object):
    def __init__(self, title, intro, content):
        self.title = title
        self.intro = intro
        self.content = content

class StatesList(Section):
    def __init__(self, title, content):
        super(StatesList, self).__init__(title, u'', content)

class Article(Section):
    def __init__(self, title, intro, content, number, newtag, oldtag, name, sep):
        super(Article, self).__init__(title, intro, content)
        self.number = number
        self.name = name
        self.newtag = newtag
        self.oldtag = oldtag
        # ': ' for all except for japanese where it's '\uFFA1'
        self.sep = sep
        for regs in content:
            regs.parent = self

    def depth(self):
        return 1


class TableOfContent(Section):
    def __init__(self, title, intro, content):
        super(TableOfContent, self).__init__(title, intro, content)
        self.articles = []

    def set_articles(self, articles):
        self.articles = articles

class Subsection(Section):
    def __init__(self, title, intro, content):
        super(Subsection, self).__init__(title, intro, content)

def split_rule_number(number):
    retval = []
    for elem in number:
        if elem.isdigit():
            if len(retval) > 0 and isinstance(retval[-1], int):
                retval[-1] = retval[-1] * 10 + int(elem)
            else:
                retval.append(int(elem))
        else:
            retval.append(str(elem))
            # Trick to be able to use list comparison for guidelines
            retval.append(0)
    return retval

@total_ordering
class Rule(object):
    def __init__(self, number, text, parent):
        self.number = number.decode("utf8")
        self.list_number = split_rule_number(self.number)
        self.text = text
        self.parent = parent
        self.children = []

    def add_child(self, rule):
        self.children.append(rule)

    def depth(self):
        length = len(self.list_number)
        return length if self.list_number[-1] != 0 else length - 1

    def __eq__(self, other):
        return self.number == other.number

    def __lt__(self, other):
        return self.list_number < other.list_number

    def __hash__(self):
        return hash(self.number)

class Regulation(Rule):
    def __init__(self, number, text, parent):
        super(Regulation, self).__init__(number, text, parent)

class Guideline(Rule):
    def __init__(self, number, text, labelname):
        super(Guideline, self).__init__(number, text, None)
        self.labelname = labelname

    @property
    def regname(self):
        return self.number.replace('+', '')

class State(object):
    def __init__(self, state_id, continent_id, name, friendly_id, info):
        self.state_id = state_id
        self.continent_id = continent_id
        self.name = name
        self.friendly_id = friendly_id
        self.info = info

class LabelDecl(object):
    def __init__(self, name, text):
        self.name = name
        self.text = text

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self.name.__eq__(other)
        elif isinstance(other, LabelDecl):
            return self.name.__eq__(other.name)
        else:
            return False

    def __hash__(self):
        return hash(self.name)


class ASTVisitor(object):
    '''
    Basic ASTVisitor. Should never be instanciated, please use
    RegulationsASTVisitor or GuidelinesASTVisitor below as base class.
    '''
    def __init__(self):
        self.rootnode_type = None

    def visit(self, o):
        if self.rootnode_type is None:
            self.rootnode_type = o.__class__
        name = "visit" + o.__class__.__name__
        method = getattr(self, name, None)
        if method is None or not callable(method):
            print "Unable to visit " + o.__class__.__name__
            return False
        return method(o)

    def visitlist(self, o):
        retval = [self.visit(i) for i in o]
        return retval.count(False) == 0

    def visitunicode(self, s):
        return True

    def visitLabelDecl(self, label):
        return True

    def visitSection(self, section):
        return self.visit(section.intro) and self.visit(section.content)

    def visitStatesList(self, section):
        return self.visit(section.intro) and self.visit(section.content)

    def visitSubsection(self, subsection):
        return self.visit(subsection.intro) and self.visit(subsection.content)

    def visitTableOfContent(self, toc):
        return True

    def visitArticle(self, article):
        return self.visit(article.intro) and self.visit(article.content)

    def visitWCADocument(self, document):
        retval = self.visit(document.sections)
        return retval and self.end_of_document(document)

    def visitWCAGuidelines(self, regs):
        return self.visitWCADocument(regs)

    def visitWCARegulations(self, regs):
        return self.visitWCADocument(regs)

    def visitWCAStates(self, states):
        return self.visitWCADocument(states)

    def visitState(self, state):
        return True

    def visitRule(self, rule):
        return True

    def visitGuideline(self, reg):
        self.visitRule(reg)
        return True

    def visitRegulation(self, reg):
        return self.visitRule(reg) and self.visit(reg.children)

    def end_of_document(self, document):
        return True

# FIXME not even sure this utility belongs here
class Ruleset(ASTVisitor):
    def __init__(self):
        super(Ruleset, self).__init__()
        self.ruleset = set()

    def visitRule(self, rule):
        self.ruleset.add(rule.number)
        return True

    def get(self, ast):
        self.ruleset = set()
        if self.visit(ast):
            return self.ruleset
        else:
            return None

