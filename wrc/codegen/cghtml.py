"""Backend for HTML."""

import re

from wrc.codegen.cg import CGDocument, GenerationOptions
from wrc.sema.ast import LabelDecl, Rule, Ruleset

REPO_REG = "https://github.com/thewca/wca-regulations"
REPO_TRANS = "https://github.com/thewca/wca-regulations-translations"
BRANCH_REG = "official"
BRANCH_TRANS = "main"
ID_REG = "official"
ID_TRANS = "wca-regulations-translations"
TOC_ELEM = '<li>{name}{sep}<a href="#{anchor}">{title}</a></li>\n'
H2 = '<h2 id="{anchor}">{title}</h2>\n'
H3 = '<h3 id="{anchor}">{title}</h3>\n'
PROVIDE = "<% provide(:title, '{title}') %>\n"
TITLE = "<h1>{title}</h1>\n"
VERSION = '<div class="version">{version}<br/>{gitlink}</div>\n'
GITLINK = (
    '[<code><a href="{repo}/tree/{branch}/{gitdir}">{identifier}</a>'
    ':<a href="{repo}/commits/{version}">{version}</a></code>]'
)

# Some homemade basics non-robust md2html functions
# We could also call pandoc to do the conversion but it's awfully slow, and the
# md subset implemented right now is sufficient for the Regulations needs


def anchorizer(text):
    """Turn a text into an acceptable anchor name"""
    return text.lower().replace(" ", "-")


def special_links_replace(text, urls):
    """
    Replace simplified Regulations and Guidelines links into actual links.
    'urls' dictionary is expected to provide actual links to the targeted
    Regulations and Guidelines, as well as to the PDF file.
    """
    match_number = r"([A-Za-z0-9]+)" + r"(\+*)"
    reference_list = [
        (r"regulations:article:" + match_number, urls["regulations"]),
        (r"regulations:regulation:" + match_number, urls["regulations"]),
        (r"guidelines:article:" + match_number, urls["guidelines"]),
        (r"guidelines:guideline:" + match_number, urls["guidelines"]),
    ]
    anchor_list = [
        (r"regulations:contents", urls["regulations"] + r"#contents"),
        (r"guidelines:contents", urls["guidelines"] + r"#contents"),
        (r"regulations:top", urls["regulations"] + r"#"),
        (r"guidelines:top", urls["guidelines"] + r"#"),
        (r"link:pdf", urls["pdf"] + ".pdf"),
    ]
    retval = text
    for match, repl in reference_list:
        retval = re.sub(match, repl + r"#\1\2", retval)
    for match, repl in anchor_list:
        retval = re.sub(match, repl, retval)
    return retval


def list2html(text):
    """
    Very simple replacement for lists, no nesting, not even two lists in the
    same 'text'... (yet sufficient for the current regulations)
    Assumes list is in a paragraph.
    """
    match = r"- (.+)\n"
    replace = r"<li>\1</li>\n"
    text = re.sub(match, replace, text)
    # Set start of list
    text = text.replace("<li>", "</p><ul><li>", 1)
    # Set end of list
    tmp = text.rsplit("</li>", 1)
    return "</li></ul><p>".join(tmp)


def link2html(text):
    """Turns md links to html"""
    match = r"\[([^\]]+)\]\(([^)]+)\)"
    replace = r'<a href="\2">\1</a>'
    return re.sub(match, replace, text)


def simple_md2html(text, urls):
    """Convert a text from md to html"""
    retval = special_links_replace(text, urls)
    # Create a par break for double newlines
    retval = re.sub(r"\n\n", r"</p><p>", retval)
    # Create a visual br for every new line
    retval = re.sub(r"\n", r"<br />\n", retval)
    # Do we really need this ? Help reduce the diff to only '\n' diff.
    retval = re.sub(r'"', r"&quot;", retval)
    retval = list2html(retval)
    return link2html(retval)


class WCADocumentHtml(CGDocument):
    """Emit html formatted to fit in the WCA website."""

    name = "HTML"

    def __init__(
        self, versionhash, language, pdf, generation_options: GenerationOptions
    ):
        super().__init__(str, generation_options=generation_options)
        self.regset = set()
        if generation_options.merged:
            self.urls = {"regulations": "./", "guidelines": "./", "pdf": pdf}
        else:
            self.urls = {
                "regulations": "./",
                "guidelines": "./guidelines.html",
                "pdf": pdf,
            }
        self.language = language

        is_translation = language != "english"
        repo = REPO_TRANS if is_translation else REPO_REG
        branch = BRANCH_TRANS if is_translation else BRANCH_REG
        gid = ID_TRANS if is_translation else ID_REG
        gdir = language if is_translation else ""

        self.gitlink = GITLINK.format(
            repo=repo, branch=branch, identifier=gid, version=versionhash, gitdir=gdir
        )
        # Overridable attributes
        self.emit_rails_header = True
        self.emit_toc = True
        self.harticle = (
            '<div id="{anchor}"><div id="{old}">'
            '<h2 id="article-{anchor}-{new}"> '
            '<a href="#article-{anchor}-{new}">{name}</a>{sep}{title}'
            "</h2></div></div>\n"
        )
        self.label = (
            '<li><span class="{name} label label-default">{name}</span> {text}</li>\n'
        )
        self.multiplus_guideline = (
            '<li id="{id}"><a href="#{id}">{id}</a>) '
            '<span class="{label} label {linked}">'
            "<a {attr}>{label}</a></span> {text}</span></li>\n"
        )
        self.plus_n_guideline = (
            '<li id="{id}"><span id="{legacy_multiplus_id}"><a href="#{id}">{id}</a>) '
            '<span class="{label} label {linked}">'
            "<a {attr}>{label}</a></span> {text}</span></li>\n"
        )
        self.regulation = '<li id="{i}"><a href="#{i}">{i}</a>) {text}'
        self.postreg = "</li>\n"

    def md2html(self, text):
        """Use the simple markdown to html converter with our URLs"""
        return simple_md2html(text, self.urls)

    def generate_ul(self, a_list):
        """Determines if we should generate th 'ul' around the list 'a_list'"""
        return len(a_list) > 0 and (isinstance(a_list[0], Rule | LabelDecl))

    def visitWCADocument(self, document):
        self.codegen += '<div class="container">'
        self.codegen += TITLE.format(title=document.title)
        self.codegen += VERSION.format(version=document.version, gitlink=self.gitlink)
        retval = [self.visit(s) for s in document.sections]
        self.codegen += "</div>\n"
        # FIXME do we really need ascii html entities instead of plain utf8 ?
        self.codegen = self.codegen.encode("ascii", "xmlcharrefreplace").decode("utf-8")
        # Let's provide the title in utf8, Rails should be able to handle it
        if self.emit_rails_header:
            self.codegen = PROVIDE.format(title=document.title) + self.codegen
        return retval.count(False) == 0

    def visitlist(self, o):
        genul = self.generate_ul(o)
        if genul:
            self.codegen += "\n<ul>\n"
        retval = super().visitlist(o)
        if genul:
            self.codegen += "</ul>\n"
        return retval

    def visitstr(self, s):
        if len(s) > 0:
            self.codegen += "<p>" + self.md2html(s) + "</p>\n"
        return True

    def visitTableOfContent(self, toc) -> bool:
        self.codegen += H2.format(anchor="contents", title=self.md2html(toc.title))
        retval = super().visit(toc.intro)
        if self.emit_toc:
            self.codegen += '<p><ul id="table_of_contents">\n'
            for article in toc.articles:
                anchorname = "article-" + article.number + "-" + article.newtag
                self.codegen += TOC_ELEM.format(
                    name=article.name,
                    anchor=anchorname,
                    title=article.title,
                    sep=article.sep,
                )
            self.codegen += "</ul>\n</p>\n"
        return retval

    def visitSection(self, section):
        self.codegen += H2.format(anchor=anchorizer(section.title), title=section.title)
        return super().visitSection(section)

    def visitArticle(self, article):
        self.codegen += self.harticle.format(
            anchor=article.number,
            old=article.oldtag,
            new=article.newtag,
            name=article.name,
            title=article.title,
            sep=article.sep,
        )
        retval = super().visit(article.intro)
        retval = retval and super().visit(article.content)
        return retval

    def visitSubsection(self, subsection):
        if self.shouldEmitSubsection(self.language, subsection.title):
            self.codegen += H3.format(
                anchor=anchorizer(subsection.title), title=subsection.title
            )
            return super().visitSubsection(subsection)
        return True

    def visitRegulation(self, reg):
        self.codegen += self.regulation.format(
            i=reg.number, text=self.md2html(reg.text)
        )
        retval = super().visitRegulation(reg)
        self.codegen += self.postreg
        return retval

    def visitLabelDecl(self, decl):
        self.codegen += self.label.format(name=decl.name, text=decl.text)
        return True

    def visitGuideline(self, guide):
        reg = guide.regname
        linked = reg in self.regset
        label_class = "linked" if linked else ""
        link_attr = 'href="{}#{}"'.format(self.urls["regulations"], reg)
        anchor_attr = f'id="#{guide.number}"'
        attr = link_attr if linked else anchor_attr

        plus_n_match = re.match(r"([a-zA-Z0-9]+)[+](\d+)", guide.number)
        if plus_n_match:
            number_legacy = plus_n_match.group(1) + "+" * int(plus_n_match.group(2))
            self.codegen += self.plus_n_guideline.format(
                id=guide.number,
                legacy_multiplus_id=number_legacy,
                text=self.md2html(guide.text),
                label=guide.labelname,
                linked=label_class,
                attr=attr,
            )
        else:
            self.codegen += self.multiplus_guideline.format(
                id=guide.number,
                text=self.md2html(guide.text),
                label=guide.labelname,
                linked=label_class,
                attr=attr,
            )
        return super().visitGuideline(guide)

    def emit(self, ast_reg, ast_guide):
        self.regset = Ruleset().get(ast_reg)
        return super().emit(ast_reg, ast_guide)
