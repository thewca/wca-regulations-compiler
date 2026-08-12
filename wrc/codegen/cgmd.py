'''
Backend for the source markdown.

This emits the format the compiler itself consumes, so a document that has been
run through the translation pass can be written back out as a translation of
wca-regulations.md. It knows nothing about catalogs: by the time it runs, the
AST already holds whichever language is being emitted.
'''
from wrc.sema.ast import Guideline
from wrc.codegen.cg import CGDocument

INDENT = '    '
TITLE = '# <wca-title>{title}\n\n'
VERSION = '<version>{version}\n'
HEADERSEC = '\n\n## {title}\n'
TOC = '\n<table-of-contents>\n'
HEADERSUBSEC = '\n### {title}\n'
LABELDECL = '- <label>[{name}] {text}\n'
ARTICLEHEADER = '\n\n## <article-{number}><{new}><{old}> {name}{sep}{title}\n'
RULE = '{indent}- {number}) {text}\n'
GUIDELINE = '{indent}- {number}) [{label}] {text}\n'


class WCADocumentMarkdown(CGDocument):
    ''' Emit the markdown the compiler itself consumes. '''

    name = "Markdown"

    def __init__(self, versionhash, language, pdf):
        # The document is regenerated from source, so the git hash, the pdf
        # naming and the per language build options the published formats need
        # do not apply here.
        del versionhash, language, pdf
        super(WCADocumentMarkdown, self).__init__(str)

    def paragraphs(self, text):
        ''' A block of prose, preceded by a blank line. '''
        return '\n%s\n' % text.rstrip('\n') if text else ''

    def visitWCADocument(self, document):
        self.codegen += TITLE.format(title=document.title)
        self.codegen += VERSION.format(version=document.version)
        retval = [self.visit(section) for section in document.sections]
        return retval.count(False) == 0

    def visitSection(self, section):
        self.codegen += HEADERSEC.format(title=section.title)
        self.codegen += self.paragraphs(section.intro)
        return self.visit(section.content)

    def visitTableOfContent(self, toc):
        # The heading keeps its <contents> tag and link target; only the label
        # between the brackets is ever translated.
        self.codegen += HEADERSEC.format(title=toc.title)
        self.codegen += self.paragraphs(toc.intro)
        self.codegen += TOC
        return True

    def visitSubsection(self, subsection):
        self.codegen += HEADERSUBSEC.format(title=subsection.title)
        self.codegen += self.paragraphs(subsection.intro)
        if subsection.content:
            self.codegen += '\n'
        return self.visit(subsection.content)

    def visitLabelDecl(self, decl):
        self.codegen += LABELDECL.format(name=decl.name, text=decl.text)
        return True

    def visitArticle(self, article):
        self.codegen += ARTICLEHEADER.format(
            number=article.number, new=article.newtag, old=article.oldtag,
            name=article.name, sep=article.sep, title=article.title)
        self.codegen += self.paragraphs(article.intro)
        self.codegen += '\n'
        # Rules are walked here rather than through the visitor because the
        # indentation depends on how deep in the tree they sit.
        self.emit_rules(article.content, 0)
        return True

    def emit_rules(self, rules, depth):
        for rule in rules:
            if isinstance(rule, Guideline):
                self.codegen += GUIDELINE.format(
                    indent=INDENT * depth, number=rule.number,
                    text=rule.text, label=rule.labelname)
            else:
                self.codegen += RULE.format(indent=INDENT * depth,
                                            number=rule.number, text=rule.text)
            self.emit_rules(rule.children, depth + 1)
