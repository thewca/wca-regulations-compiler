"""Backend for PDF using html."""

import os.path
from importlib.resources import as_file, files
from pathlib import Path

from wrc.codegen.cghtml import WCADocumentHtml
from wrc.sema.ast import Article, LabelDecl, Rule

CSS_FONTS = """
@font-face {{
    font-family: "Computer Modern";
    src: url("{normal}");
    font-weight: normal;
    font-style: normal;
}}
@font-face {{
    font-family: "Computer Modern";
    src: url("{bold}");
    font-weight: bold;
    font-style: normal;
}}
@font-face {{
    font-family: "Computer Modern";
    src: url("{italic}");
    font-weight: normal;
    font-style: italic, oblique;
}}
@font-face {{
    font-family: "Computer Modern";
    src: url("{bi}");
    font-weight: bold;
    font-style: italic, oblique;
}}
"""
TITLE = "WCA Regulations"
AUTHOR = "WCA Regulations Committee"
HTML_TITLE = (
    '<div class="title">{title}</div>'
    '<div class="author">{author}</div>'
    '<div class="spacer"></div>'
)
NO_BREAK = '<div class="no_break_inside">'


class WCADocumentHtmlToPdf(WCADocumentHtml):
    """Emit html suitable to be printed to PDF using wkhtmltopdf"""

    name = "PDF"

    def __init__(self, versionhash, language, pdf):
        super().__init__(versionhash, language, pdf)
        self.urls = {"regulations": "", "guidelines": "", "pdf": pdf}
        self.emit_rails_header = False
        self.emit_toc = False
        self.harticle = (
            '<div id="{anchor}"></div>'
            '<h2 id="article-{anchor}-{new}"> '
            "{name}{sep}{title}"
            "</h2>\n"
        )
        self.label = (
            '<li>[<span class="{name} label label-default">{name}</span>] {text}</li>\n'
        )
        self.guideline = (
            '<li id="{i}" class="rule">{i}) '
            '<span class="{label} label {linked}">'
            "[<a {attr}>{label}</a>]</span> {text}</li>\n"
        )
        # Here we intentionally break the hierarchy (ul(li(ul(li))li()) turns to
        # ul(li()ul(li())li()) to be able to "easily" avoid  page breaking
        # inside a 'li' text (it does weird stuff if the whole element has to
        # avoid page-breaking
        self.regulation = '<li id="{i}" class="rule">{i}) {text}</li>\n'
        self.postreg = ""
        # Internal variable to handle grouping between a h* and its first element
        self.group_closed = True

    def generate_ul(self, a_list):
        # Here we don't want to generate 'ul' for the root rule, we want to group
        # the first 'li' with the header to force avoiding page-break
        return len(a_list) > 0 and (
            (isinstance(a_list[0], Rule) and not isinstance(a_list[0].parent, Article))
            or isinstance(a_list[0], LabelDecl)
        )

    def no_break(self):
        if self.group_closed:
            self.group_closed = False
            # This first div will be closed after the first paragraph
            self.codegen += NO_BREAK

    def visitArticle(self, article):
        self.no_break()
        return super().visitArticle(article)

    def visitSection(self, section):
        self.no_break()
        return super().visitSection(section)

    def visitSubsection(self, subsection):
        self.no_break()
        return super().visitSubsection(subsection)

    def visitTableOfContent(self, toc):
        self.no_break()
        return super().visitTableOfContent(toc)

    def visitstr(self, s):
        retval = super().visitstr(s)
        if len(s) > 0 and not self.group_closed:
            # We are in an introduction paragraph and we want to group it
            # with the article's h2
            self.group_closed = True
            self.codegen += "</div>"
        return retval

    def visitRule(self, rule):
        # This one is called after the Rule's 'li' is emitted, we override
        # the call iterating through the Rule's children
        if not self.group_closed:
            self.group_closed = True
            self.codegen += "</div>"
        return super().visitRule(rule)

    def visitWCARegulations(self, regs):
        self.codegen += "<html><head>"
        self.codegen += f"<title>{TITLE}</title>"
        self.codegen += '<style media="all">\n'
        # Output the font faces for our custom fonts, shipped with the package
        fonts: dict[str, str | Path] = {
            "normal": "cmunrm.otf",
            "italic": "cmunti.otf",
            "bold": "cmunbx.otf",
            "bi": "cmunbi.otf",
        }
        for name in fonts:  # noqa: PLC0206
            resource = files("wrc").joinpath(f"data/{fonts[name]}")
            with as_file(resource) as fontfile_path:
                if not os.path.isabs(fontfile_path):
                    fontfile_path = os.path.abspath(fontfile_path)
                fonts[name] = fontfile_path
        self.codegen += CSS_FONTS.format(
            normal=fonts["normal"],
            bold=fonts["bold"],
            italic=fonts["italic"],
            bi=fonts["bi"],
        )
        self.codegen += (
            files("wrc").joinpath("data/htmltopdf.css").read_text(encoding="utf-8")
        )
        self.codegen += f'</style></head><body class="{self.language}"><div>\n'
        self.codegen += HTML_TITLE.format(title=TITLE, author=AUTHOR)
        retval = super().visitWCARegulations(regs)
        self.codegen += '<div class="page_break"></div>\n'
        return retval

    def visitWCAGuidelines(self, guides):
        retval = super().visitWCAGuidelines(guides)
        self.codegen += "</div></body></html>\n"
        return retval
