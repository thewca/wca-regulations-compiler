import re
from wrc.sema.ast import Ruleset, Rule, LabelDecl, Article
from wrc.codegen.cg import CGDocument

REPO_REG = "https://github.com/cubing/wca-regulations"
REPO_TRANS = "https://github.com/cubing/wca-regulations-translations"
BRANCH_REG = "official"
BRANCH_TRANS = "master"
ID_REG = "official"
ID_TRANS = "wca-regulations-translations"
TOC_ELEM = u'<li>{name}{sep}<a href="#{anchor}">{title}</a></li>\n'
H2 = u'<h2 id="{anchor}">{title}</h2>\n'
H3 = u'<h3 id="{anchor}">{title}</h3>\n'
PROVIDE = u"<% provide(:title, '{title}') %>\n"
TITLE = u'<h1>{title}</h1>\n'
VERSION = u'<div class="version">{version}<br/>{gitlink}</div>\n'
GITLINK = (u'[<code><a href="{repo}/tree/{branch}/{gitdir}">{identifier}</a>'
           ':<a href="{repo}/commits/{version}">{version}</a></code>]')

# Some homemade basics non-robust md2html functions
# We could also call pando to do the conversion but it's awfully slow

def anchorizer(text):
    return text.lower().replace(" ", "-")


def special_links_replace(text, urls):
    regOrGuide2Slots = r'([A-Za-z0-9]+)' + r'(\+*)'
    reference_list = [(r'regulations:article:' + regOrGuide2Slots, urls['regulations']),
                      (r'regulations:regulation:' + regOrGuide2Slots, urls['regulations']),
                      (r'guidelines:article:' + regOrGuide2Slots, urls['guidelines']),
                      (r'guidelines:guideline:' + regOrGuide2Slots, urls['guidelines']),
                     ]
    anchor_list = [(r'regulations:contents', urls['regulations'] + r'#contents'),
                   (r'guidelines:contents', urls['guidelines'] + r'#contents'),
                   (r'regulations:top', urls['regulations'] + r'#'),
                   (r'guidelines:top', urls['guidelines'] + r'#'),
                   (r'link:pdf', urls['pdf'] + '.pdf'),
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

def simple_md2html(text, urls):
    retval = special_links_replace(text, urls)
    # Create a br for every 4 spaces
    retval = re.sub(r'[ ]{4}\n', r'<br />\n', retval)
    # Do we really need this ? Help reduce the diff to only '\n' diff.
    retval = re.sub(r'"', r'&quot;', retval)
    return link2html(retval)


class WCADocumentHtml(CGDocument):
    def __init__(self, versionhash, language, pdf):
        super(WCADocumentHtml, self).__init__()
        self.codegen = u""
        self.regset = set()
        self.urls = {'regulations': './', 'guidelines': './guidelines.html',
                     'pdf': pdf}

        is_translation = (language != "english")
        repo = REPO_TRANS if is_translation else REPO_REG
        branch = BRANCH_TRANS if is_translation else BRANCH_REG
        gid = ID_TRANS if is_translation else ID_REG
        gdir = language if is_translation else ""

        self.gitlink = GITLINK.format(repo=repo, branch=branch, identifier=gid,
                                      version=versionhash, gitdir=gdir)
        # Overridable attributes
        self.emit_rails_header = True
        self.emit_toc = True
        self.harticle = (u'<div id="{anchor}"><div id="{old}">'
                          '<h2 id="article-{anchor}-{new}"> '
                          '<a href="#article-{anchor}-{new}">{name}</a>{sep}{title}'
                          '</h2></div></div>\n')
        self.label = (u'<li><span class="{name} label label-default">{name}</span> '
                       '{text}</li>\n')
        self.guideline = (u'<li id="{i}"><a href="#{i}">{i}</a>) '
                           '<span class="{label} label {linked}">'
                           '<a {attr}>{label}</a></span> {text}</li>\n')
        self.regulation = u'<li id="{i}"><a href="#{i}">{i}</a>) {text}'
        self.postreg = u'</li>\n'

    def md2html(self, text):
        return simple_md2html(text, self.urls)

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
        if self.emit_rails_header:
            self.codegen = (PROVIDE.format(title=document.title).encode('utf8')
                            + str(self.codegen))
        return retval.count(False) == 0

    def generate_ul(self, a_list):
        return len(a_list) > 0 and (isinstance(a_list[0], Rule) or
                                    isinstance(a_list[0], LabelDecl))

    def visitlist(self, o):
        genul = self.generate_ul(o)
        if genul:
            self.codegen += '\n<ul>\n'
        retval = super(WCADocumentHtml, self).visitlist(o)
        if genul:
            self.codegen += "</ul>\n"
        return retval

    def visitunicode(self, u):
        if len(u) > 0:
            self.codegen += "<p>" + self.md2html(u) + "</p>\n"
        return True

    def visitTableOfContent(self, toc):
        self.codegen += H2.format(anchor="contents",
                                  title=self.md2html(toc.title))
        retval = super(WCADocumentHtml, self).visit(toc.intro)
        if self.emit_toc:
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
        self.codegen += self.harticle.format(anchor=article.number,
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

    def visitRegulation(self, reg):
        self.codegen += self.regulation.format(i=reg.number,
                                               text=self.md2html(reg.text))
        retval = super(WCADocumentHtml, self).visitRegulation(reg)
        self.codegen += self.postreg
        return retval


    def visitLabelDecl(self, decl):
        self.codegen += self.label.format(name=decl.name, text=decl.text)
        return True

    def visitGuideline(self, guide):
        reg = guide.regname
        linked = reg in self.regset
        label_class = "linked" if linked else ""
        link_attr = 'href="%s#%s"' % (self.urls['regulations'], reg)
        anchor_attr = 'id="#%s"' % guide.number
        attr = link_attr if linked else anchor_attr

        self.codegen += self.guideline.format(i=guide.number,
                                              text=self.md2html(guide.text),
                                              label=guide.labelname,
                                              linked=label_class,
                                              attr=attr)
        return super(WCADocumentHtml, self).visitGuideline(guide)

    def emit(self, ast_reg, ast_guide):
        self.regset = Ruleset().get(ast_reg)
        self.visit(ast_reg)
        codegen_reg = self.codegen
        self.codegen = u""
        self.visit(ast_guide)
        return (codegen_reg, self.codegen)




