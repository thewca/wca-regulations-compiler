class WCADocument(object):
    def __init__(self, title, version, sections):
        self.title = title
        self.sections = sections
        self.version = version

class WCARegulations(WCADocument):
    def __init__(self, title, version, sections):
        super(WCARegulations, self).__init__(title, version, sections)

class WCAGuidelines(WCADocument):
    def __init__(self, title, version, sections):
        super(WCAGuidelines, self).__init__(title, version, sections)

class Section(object):
    def __init__(self, title, intro, content):
        self.title = title
        self.intro = intro
        self.content = content
        # print "Buildind section " + title
        # print "Intro size : " + str(len(intro))
        # print "Content size : " + str(len(content))

    def __str__(self):
        return self.title

class Article(Section):
    def __init__(self, title, intro, content, number, newtag, oldtag, name):
        super(Article, self).__init__(title, intro, content)
        self.number = number
        self.name = name
        self.newtag = newtag
        self.oldtag = oldtag
        for regs in content:
            regs.parent = self

class TableOfContent(Section):
    def __init__(self, title, intro, content):
        super(TableOfContent, self).__init__(title, intro, content)
        self.articles = []

    def set_articles(self, articles):
        self.articles = articles

    def __str__(self):
        retval = self.title + "\n"
        for a in self.articles:
            retval += str(a) + "\n"
        return retval

class Subsection(Section):
    def __init__(self, title, intro, content):
        super(Subsection, self).__init__(title, intro, content)
        # print "Building Subsection " + title

def split_rule_number(number):
    retval = []
    for elem in number:
        if elem.isdigit():
            if len(retval) > 0 and isinstance(retval[-1], int):
                retval[-1] *= 10
                retval[-1] += int(elem)
            else:
                retval.append(int(elem))
        else:
            retval.append(str(elem))
            # Trick to be able to use list comparison for guidelines
            retval.append(0)
    return retval

class Rule(object):
    def __init__(self, number, text, parent):
        self.number = number
        self.text = text
        self.parent = parent
        self.children = []

    def add_child(self, rule):
        self.children.append(rule)

    def __lt__(self, other):
        return (split_rule_number(self.number)
                < split_rule_number(other.number))

    def __hash__(self):
        return hash(self.number)

class Regulation(Rule):
    def __init__(self, number, text, parent):
        super(Regulation, self).__init__(number, text, parent)

class Guideline(Rule):
    def __init__(self, number, text, label):
        super(Guideline, self).__init__(number, text, None)
        self.label = label

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

    def __str__(self):
        return self.name


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

    def visitstr(self, s):
        return True

    def visitLabelDecl(self, label):
        return True

    def visitSection(self, section):
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

    def visitGuideline(self, reg):
        return True

    def visitRegulation(self, reg):
        return self.visit(reg.children)

    def end_of_document(self, document):
        return True

