import re
from wrc.sema.ast import WCAGuidelines, WCARegulations, Ruleset,\
                     Rule, LabelDecl
from wrc.codegen.cg import CGDocument

PDF_LINK = "wca-regulations-and-guidelines.pdf"
REPO_REG = "https://github.com/cubing/wca-regulations"
REPO_TRANS = "https://github.com/cubing/wca-regulations-translations"
BRANCH_REG = "official"
BRANCH_TRANS = "master"
ID_REG = "official"
ID_TRANS = "wca-regulations-translations"
TOC_ELEM = u'<li>{name}{sep}<a href="#{anchor}">{title}</a></li>\n'
H2 = u'<h2 id="{anchor}">{title}</h2>\n'
H3 = u'<h3 id="{anchor}">{title}</h3>\n'
HARTICLE = (u'<span id="{anchor}"></span><span id="{old}"></span>'
            '<h2 id="article-{anchor}-{new}"> '
            '<a href="#article-{anchor}-{new}">{name}</a>{sep}{title}'
            '</h2>\n')
PROVIDE = u"<% provide(:title, '{title}') %>\n"
TITLE = u'<h1>{title}</h1>\n'
VERSION = u'<div class="version">{version}<br/>{gitlink}</div>\n'
GITLINK = (u'[<code><a href="{repo}/tree/{branch}/{gitdir}">{identifier}</a>'
           ':<a href="{repo}/commits/{version}">{version}</a></code>]')
GUIDELINE = (u'<li id="{i}"><a href="#{i}">{i}</a>) '
             '<span class="{label} label {linked}"><a {attr}>{label}</a></span>'
             ' {text}</li>\n')
LABEL = (u'<li><span class="example {name} label label-default">{name}</span> '
         '{text}</li>\n')
REGULATION = u'<li id="{i}"><a href="#{i}">{i}</a>) {text}'
POSTREG = u'</li>\n'

# Some homemade basics non-robust md2html functions
# We could also call pando to do the conversion but it's awfully slow

def anchorizer(text):
    return text.lower().replace(" ", "-")


def special_links_replace(text):
    regOrGuide2Slots = r'([A-Za-z0-9]+)' + r'(\+*)'
    regsURL = "./"
    guidesURL = "guidelines.html"
    reference_list = [(r'regulations:article:' + regOrGuide2Slots, regsURL),
                      (r'regulations:regulation:' + regOrGuide2Slots, regsURL),
                      (r'guidelines:article:' + regOrGuide2Slots, guidesURL),
                      (r'guidelines:guideline:' + regOrGuide2Slots, guidesURL),
                     ]
    anchor_list = [(r'regulations:contents', regsURL + r'#contents'),
                   (r'guidelines:contents', guidesURL + r'#contents'),
                   (r'regulations:top', regsURL),
                   (r'guidelines:top', guidesURL),
                   (r'link:pdf', PDF_LINK),
                  ]
    retval = text
    for match, repl in reference_list:
        retval = re.sub(match, repl + r'#\1\2', retval)
    for match, repl in anchor_list:
        retval = re.sub(match, repl, retval)
    return retval

def link2html(text):
    match = r'\[([^\]]+)\]\(([^)]+)\)'
    replace = r'<a href="\2">\1</a>'
    return re.sub(match, replace, text)

def simple_md2html(text):
    retval = special_links_replace(text)
    # Create a br for every 4 spaces
    retval = re.sub(r'[ ]{4}\n', r'<br />\n', retval)
    # Do we really need this ? Help reduce the diff to only '\n' diff.
    retval = re.sub(r'"', r'&quot;', retval)
    return link2html(retval)


class WCADocumentHtml(CGDocument):
    def __init__(self, versionhash, language):
        super(WCADocumentHtml, self).__init__()
        self.codegen = u""

        is_translation = (language != "english")
        repo = REPO_TRANS if is_translation else REPO_REG
        branch = BRANCH_TRANS if is_translation else BRANCH_REG
        gid = ID_TRANS if is_translation else ID_REG
        gdir = language if is_translation else ""

        self.gitlink = GITLINK.format(repo=repo, branch=branch, identifier=gid,
                                      version=versionhash, gitdir=gdir)

    def visitWCADocument(self, document):
        # self.codegen += self.str_provide.format(title=document.title)
        self.codegen += '<div class="container">'
        self.codegen += TITLE.format(title=document.title)
        self.codegen += VERSION.format(version=document.version,
                                       gitlink=self.gitlink)
        retval = [self.visit(s) for s in document.sections]
        self.codegen += "</div>\n"
        # Codegen is a Unicode
        # FIXME do we really need ascii html entities instead of plain utf8 ?
        self.codegen = self.codegen.encode('ascii', 'xmlcharrefreplace')
        # Now codegen is a str
        # Let's provide the title in utf8, Rails should be able to handle it
        self.codegen = (PROVIDE.format(title=document.title).encode('utf8')
                        + str(self.codegen))
        return retval.count(False) == 0

    def visitlist(self, o):
        genul = len(o) > 0 and (isinstance(o[0], Rule) or isinstance(o[0], LabelDecl))
        if genul:
            self.codegen += "\n<ul>\n"
        retval = super(WCADocumentHtml, self).visitlist(o)
        if genul:
            self.codegen += "</ul>\n"
        return retval

    def visitunicode(self, u):
        if len(u) > 0:
            self.codegen += "<p>" + simple_md2html(u) + "</p>\n"
        return True

    def visitTableOfContent(self, toc):
        self.codegen += H2.format(anchor="contents",
                                  title=simple_md2html(toc.title))
        retval = super(WCADocumentHtml, self).visit(toc.intro)
        self.codegen += '<p><ul id="table_of_contents">\n'
        for article in toc.articles:
            anchorname = "article-" + article.number + "-" + article.newtag
            self.codegen += TOC_ELEM.format(name=article.name, anchor=anchorname,
                                            title=article.title, sep=article.sep)
        self.codegen += '</ul>\n</p>\n'
        return retval

    def visitSection(self, section):
        self.codegen += H2.format(anchor=anchorizer(section.title),
                                  title=section.title)
        return super(WCADocumentHtml, self).visitSection(section)

    def visitArticle(self, article):
        self.codegen += HARTICLE.format(anchor=article.number,
                                        old=article.oldtag,
                                        new=article.newtag,
                                        name=article.name,
                                        title=article.title,
                                        sep=article.sep)
        retval = super(WCADocumentHtml, self).visit(article.intro)
        retval = retval and super(WCADocumentHtml, self).visit(article.content)
        return retval

    def visitSubsection(self, subsection):
        self.codegen += H3.format(anchor=anchorizer(subsection.title),
                                  title=subsection.title)
        return super(WCADocumentHtml, self).visitSubsection(subsection)


class WCARegulationsHtml(WCADocumentHtml):
    def __init__(self, versionhash="unknown", language="english"):
        super(WCARegulationsHtml, self).__init__(versionhash, language)
        # This CG can only handle regulations
        self.doctype = WCARegulations

    def visitRegulation(self, reg):
        self.codegen += REGULATION.format(i=reg.number,
                                          text=simple_md2html(reg.text))
        retval = super(WCARegulationsHtml, self).visitRegulation(reg)
        self.codegen += POSTREG
        return retval

class WCAGuidelinesHtml(WCADocumentHtml):
    def __init__(self, regulations, versionhash="unknown", language="english"):
        super(WCAGuidelinesHtml, self).__init__(versionhash, language)
        # This CG can only handle guidelines
        self.doctype = WCAGuidelines
        self.regset = Ruleset().get(regulations)

    def visitLabelDecl(self, decl):
        self.codegen += LABEL.format(name=decl.name, text=decl.text)
        return True

    def visitGuideline(self, guide):
        reg = guide.regname
        linked = reg in self.regset
        label_class = "linked" if linked else ""
        link_attr = 'href="./#%s"' % reg
        anchor_attr = 'id="#%s"' % guide.number
        attr = link_attr if linked else anchor_attr

        self.codegen += GUIDELINE.format(i=guide.number,
                                         text=simple_md2html(guide.text),
                                         label=guide.labelname,
                                         linked=label_class,
                                         attr=attr)
        return True



