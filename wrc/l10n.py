'''
The gettext catalogs the documents are translated through, and the pass that
applies one to a parsed document.

The documents already carry language independent identifiers -- rule numbers,
article numbers, label names -- and `wrc --diff` already treats them as the
identity of a rule across languages. The catalogs reuse them as the msgctxt, so
a translation is a set of strings keyed by rule number instead of a second copy
of the document.

Structure is never stored in a catalog. Nesting, ordering, numbering and the
document skeleton all come from the English document, which is what makes it
impossible for a translation to drift out of shape the way the checked-in ones
have. A translation is produced by parsing English and swapping the strings, so
every backend -- html, pdf, json, markdown -- gets translated output from the
same pass.

Front matter prose has no identifier to borrow, so it is keyed by a slug of the
English heading it sits under. Retitling an English heading therefore drops the
old key and adds a new one: the prose below it has to be looked at again, which
is the intended outcome.
'''
import re

import polib
from unidecode import unidecode

from wrc.sema.ast import Article, Guideline, LabelDecl, Subsection, TableOfContent

# `## <contents> [Contents](regulations:contents)`. Only the bracketed text
# differs between languages, so it is the only part offered for translation:
# a translator who has to retype the tag and the link target is a translator
# who can break the build with a typo.
CONTENTS_HEADER = re.compile(r'^<contents>\s*\[(?P<title>.+)\]\((?P<target>[^)]+)\)\s*$')
CONTENTS_TEMPLATE = '<contents> [%s](%s)'

MD_LINK = re.compile(r'\[([^\]]+)\]\([^)]*\)')
TAG = re.compile(r'<[^>]+>')
NON_SLUG = re.compile(r'[^a-z0-9]+')

DOC_TITLE = 'doc:title'
DOC_VERSION = 'doc:version'
# ': ' everywhere except the CJK translations, which use the full width '：'.
# It is a genuine per language string, and keeping it in the catalog avoids a
# second source of truth in data/languages.json.
DOC_SEPARATOR = 'doc:article-separator'


def slugify(title):
    ''' Turn a heading into a key component: drop tags and link targets. '''
    text = MD_LINK.sub(r'\1', TAG.sub('', title))
    return NON_SLUG.sub('-', unidecode(text).lower()).strip('-')


def split_contents_header(heading):
    '''
    Split a table of contents heading into its translatable label and its link
    target. Both are None when the heading does not have the canonical shape.
    '''
    match = CONTENTS_HEADER.match(heading)
    if match is None:
        return None, None
    return match.group('title'), match.group('target')


def section_key(path, field):
    ''' `notes/wording:text`, for a path of heading slugs. '''
    return '%s:%s' % ('/'.join(path), field)


def article_key(number, field):
    ''' `article:A:title` '''
    return 'article:%s:%s' % (number, field)


def label_key(name, field):
    ''' `label:ADDITION:text`, keyed on the English label name. '''
    return 'label:%s:%s' % (name, field)


class Catalog(object):
    '''
    Translations to substitute, keyed by msgctxt.

    An untranslated string falls back to the English it was extracted from.
    That keeps a translated document structurally complete no matter how far
    behind the catalog is -- the gaps read as English instead of vanishing --
    and it makes applying an empty catalog a no-op, so rendering English
    through this pass reproduces the input.
    '''

    def __init__(self, translations=None):
        self.translations = translations or {}

    @classmethod
    def load(cls, path):
        ''' Read a .po/.pot file. Fuzzy entries are treated as untranslated. '''
        catalog = polib.pofile(path)
        return cls({entry.msgctxt: entry.msgstr for entry in catalog
                    if entry.msgctxt and entry.msgstr and not entry.fuzzy})

    def get(self, key, source):
        return self.translations.get(key) or source


def translate_document(document, catalog):
    '''
    Replace every translatable string in a parsed document, in place.

    Keys are always derived from the English the document was parsed from, so
    each heading's slug is taken before that heading is overwritten.
    '''
    document.title = catalog.get(DOC_TITLE, document.title)
    document.version = catalog.get(DOC_VERSION, document.version)

    articles = [s for s in document.sections if isinstance(s, Article)]
    separator = catalog.get(DOC_SEPARATOR, articles[0].sep) if articles else None

    for section in document.sections:
        if isinstance(section, Article):
            _translate_article(section, catalog, separator)
        elif isinstance(section, TableOfContent):
            _translate_contents(section, catalog)
        else:
            _translate_section(section, catalog, slugify(section.title))
    return document


def _translate_article(article, catalog, separator):
    article.name = catalog.get(article_key(article.number, 'name'), article.name)
    article.title = catalog.get(article_key(article.number, 'title'), article.title)
    article.intro = catalog.get(article_key(article.number, 'text'), article.intro)
    article.sep = separator
    _translate_rules(article.content, catalog)


def _translate_rules(rules, catalog):
    for rule in rules:
        rule.text = catalog.get(rule.number, rule.text)
        if isinstance(rule, Guideline):
            # The label name is a string in its own right, keyed on the English
            # one, so this stays correct after the declarations are translated.
            rule.labelname = catalog.get(label_key(rule.labelname, 'name'),
                                         rule.labelname)
        _translate_rules(rule.children, catalog)


def _translate_contents(toc, catalog):
    label, target = split_contents_header(toc.title)
    if label is None:
        _translate_section(toc, catalog, slugify(toc.title))
        return
    path = [slugify(label)]
    toc.title = CONTENTS_TEMPLATE % (
        catalog.get(section_key(path, 'title'), label), target)
    toc.intro = catalog.get(section_key(path, 'text'), toc.intro)


def _translate_section(section, catalog, slug):
    path = [slug]
    section.title = catalog.get(section_key(path, 'title'), section.title)
    section.intro = catalog.get(section_key(path, 'text'), section.intro)
    for item in section.content or []:
        if isinstance(item, Subsection):
            _translate_subsection(item, catalog, path + [slugify(item.title)])


def _translate_subsection(subsection, catalog, path):
    subsection.title = catalog.get(section_key(path, 'title'), subsection.title)
    subsection.intro = catalog.get(section_key(path, 'text'), subsection.intro)
    for item in subsection.content or []:
        if isinstance(item, LabelDecl):
            # Translate the text first: the name is this label's own key.
            item.text = catalog.get(label_key(item.name, 'text'), item.text)
            item.name = catalog.get(label_key(item.name, 'name'), item.name)
