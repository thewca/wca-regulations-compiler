''' Backend for HTML. '''
import re
from wrc.sema.ast import Ruleset, Rule, LabelDecl
from wrc.codegen.cg import CGDocument

REPO_REG = "https://github.com/thewca/wca-regulations"
REPO_TRANS = "https://github.com/thewca/wca-regulations-translations"
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
# We could also call pandoc to do the conversion but it's awfully slow, and the
# md subset implemented right now is sufficient for the Regulations needs

def anchorizer(text):
    ''' Turn a text into an acceptable anchor name '''
    return text.lower().replace(" ", "-")


def special_links_replace(text, urls):
    '''
    Replace simplified Regulations and Guidelines links into actual links.
    'urls' dictionary is expected to provide actual links to the targeted
    Regulations and Guidelines, as well as to the PDF file.
    '''
    match_number = r'([A-Za-z0-9]+)' + r'(\+*)'
    reference_list = [(r'regulations:article:' + match_number, urls['regulations']),
                      (r'regulations:regulation:' + match_number, urls['regulations']),
                      (r'guidelines:article:' + match_number, urls['guidelines']),
                      (r'guidelines:guideline:' + match_number, urls['guidelines']),
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

def list2html(text):
    '''
    Very simple replacement for lists, no nesting, not even two lists in the
    same 'text'... (yet sufficient for the current regulations)
    Assumes list is in a paragraph.
    '''
    match = r'- (.+)\n'
    replace = r'<li>\1</li>\n'
    text = re.sub(match, replace, text)
    # Set start of list
    text = text.replace('<li>', '</p><ul><li>', 1)
    # Set end of list
    tmp = text.rsplit('</li>', 1)
    return '</li></ul><p>'.join(tmp)

def link2html(text):
    ''' Turns md links to html '''
    match = r'\[([^\]]+)\]\(([^)]+)\)'
    replace = r'<a href="\2">\1</a>'
    return re.sub(match, replace, text)

def simple_md2html(text, urls):
    ''' Convert a text from md to html '''
    retval = special_links_replace(text, urls)
    # Create a par break for double newlines
    retval = re.sub(r'\n\n', r'</p><p>', retval)
    # Create a visual br for every new line
    retval = re.sub(r'\n', r'<br />\n', retval)
    # Do we really need this ? Help reduce the diff to only '\n' diff.
    retval = re.sub(r'"', r'&quot;', retval)
    retval = list2html(retval)
    return link2html(retval)


class WCADocumentHtml(CGDocument):
    ''' Emit html formatted to fit in the WCA website.  '''
    name = "HTML"
    def __init__(self, versionhash, language, pdf):
        super(WCADocumentHtml, self).__init__(unicode)
        self.regset = set()
        self.urls = {'regulations': './', 'guidelines': './guidelines.html',
                     'pdf': pdf}
        self.language = language

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
        ''' Use the simple markdown to html converter with our URLs '''
        return simple_md2html(text, self.urls)

    def generate_ul(self, a_list):
        ''' Determines if we should generate th 'ul' around the list 'a_list' '''
        return len(a_list) > 0 and (isinstance(a_list[0], Rule) or
                                    isinstance(a_list[0], LabelDecl))

    def visitWCADocument(self, document):
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
        return super(WCADocumentHtml, self).emit(ast_reg, ast_guide)




