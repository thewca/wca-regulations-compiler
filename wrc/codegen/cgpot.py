''' Backend for gettext PO templates. '''
import polib

from wrc.sema.ast import Article
from wrc.codegen.cg import CGDocument
from wrc.l10n import (DOC_SEPARATOR, DOC_TITLE, DOC_VERSION, article_key,
                      label_key, section_key, slugify, split_contents_header)

HEADER = {
    'Project-Id-Version': 'wca-regulations',
    'MIME-Version': '1.0',
    'Content-Type': 'text/plain; charset=UTF-8',
    'Content-Transfer-Encoding': '8bit',
}


class WCADocumentPot(CGDocument):
    '''
    Emit a translation template keyed on the identifiers already in the
    document: rule numbers, article numbers and label names.
    '''

    name = "PO template"

    def __init__(self, versionhash, language, pdf):
        # The template is always taken from English, and carries no structure,
        # so none of the language specific build options apply.
        del versionhash, language, pdf
        super(WCADocumentPot, self).__init__(list)
        self.path = []
        self.article = None

    def add(self, key, source, comment, strip=True):
        '''
        Record one translatable string. Empty strings are not offered.

        Surrounding whitespace is dropped, because it is never content: the
        Italian H2 carries a trailing space that the lexer folds into the rule
        text, and gettext rejects a catalog whose msgid and msgstr disagree
        about a trailing newline.
        '''
        if strip:
            source = source.strip()
        if source:
            self.codegen.append((key, source, comment))
        return True

    def entries(self, ast_reg, ast_guide):
        '''
        Every translatable string in document order, as (key, source, comment).

        Rule numbers are unique across the two documents, so they can share one
        catalog the way they already share one published document. The keys
        that are not -- doc:title, and a heading for every article the two
        documents have in common -- are taken from the Regulations, which are
        visited first.
        '''
        reg_entries, guide_entries = super(WCADocumentPot, self).emit(ast_reg, ast_guide)
        seen = {key for key, _, _ in reg_entries}
        reg_entries.extend(entry for entry in guide_entries if entry[0] not in seen)
        return reg_entries

    def emit(self, ast_reg, ast_guide):
        template = polib.POFile(check_for_duplicates=True)
        template.metadata = HEADER
        for key, source, comment in self.entries(ast_reg, ast_guide):
            template.append(polib.POEntry(msgctxt=key, msgid=source, msgstr='',
                                          comment=comment))
        return str(template), ""

    def visitWCADocument(self, document):
        self.add(DOC_TITLE, document.title, 'Document title')
        self.add(DOC_VERSION, document.version,
                 'Version line. Only the wording around the date is translated')
        articles = [s for s in document.sections if isinstance(s, Article)]
        if articles:
            self.add(DOC_SEPARATOR, articles[0].sep,
                     'Goes between the two halves of an article heading, as in '
                     '"Article 1: Officials". Note the trailing space; the CJK '
                     'documents use a full width colon and no space',
                     strip=False)
        retval = [self.visit(section) for section in document.sections]
        return retval.count(False) == 0

    def visitSection(self, section):
        return self.visit_headed(section, section.title)

    def visitSubsection(self, subsection):
        return self.visit_headed(subsection, subsection.title)

    def visitTableOfContent(self, toc):
        # Only the label between the brackets is translated; the tag and the
        # link target around it are structural and are re-emitted verbatim.
        title, _ = split_contents_header(toc.title)
        return self.visit_headed(toc, title if title is not None else toc.title)

    def visit_headed(self, section, title):
        ''' A heading plus the prose under it, keyed by the path of slugs. '''
        self.path.append(slugify(title))
        self.add(section_key(self.path, 'title'), title, self.heading_comment())
        self.add(section_key(self.path, 'text'), section.intro, self.heading_comment())
        retval = self.visit(section.content)
        self.path.pop()
        return retval

    def visitLabelDecl(self, decl):
        # The name is translated too: the Dutch document tags its guidelines
        # [AANVULLING], not [ADDITION]. Keying on the English name keeps the
        # two halves together no matter what the translation calls it.
        self.add(label_key(decl.name, 'name'), decl.name,
                 'Label shown in front of every guideline it is applied to. '
                 'Uppercase, no brackets')
        self.add(label_key(decl.name, 'text'), decl.text,
                 'Meaning of the %s label' % decl.name)
        return True

    def visitArticle(self, article):
        self.article = article
        self.add(article_key(article.number, 'name'), article.name,
                 'Heading of article %s, before the separator' % article.number)
        self.add(article_key(article.number, 'title'), article.title,
                 'Heading of article %s, after the separator' % article.number)
        self.add(article_key(article.number, 'text'), article.intro,
                 'Introduction to article %s' % article.number)
        retval = self.visit(article.content)
        self.article = None
        return retval

    def visitRule(self, rule):
        # A guideline's label is rendered from label:<name>:name, so it is not
        # part of the text offered here. Recursion into children is inherited.
        self.add(rule.number, rule.text, self.rule_comment(rule))
        return True

    def heading_comment(self):
        return ' > '.join(self.path)

    def rule_comment(self, rule):
        if self.article is None:
            return rule.number
        return '%s%s%s, %s' % (self.article.name, self.article.sep,
                               self.article.title, rule.number)
