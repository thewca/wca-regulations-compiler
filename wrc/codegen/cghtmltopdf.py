''' Backend for PDF using html. '''
import os.path
import pkg_resources
from wrc.sema.ast import Rule, LabelDecl, Article
from wrc.codegen.cghtml import WCADocumentHtml

CSS_FONTS = '''
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
'''
TITLE = "WCA Regulations and Guidelines"
AUTHOR = "WCA Regulations Committee"
HTML_TITLE = ('<div class="title">{title}</div>'
              '<div class="author">{author}</div>'
              '<div class="spacer"></div>')
NO_BREAK = '<div class="no_break_inside">'


class WCADocumentHtmlToPdf(WCADocumentHtml):
    ''' Emit html suitable to be printed to PDF using wkhtmltopdf '''
    name = "PDF"
    def __init__(self, versionhash, language, pdf):
        super(WCADocumentHtmlToPdf, self).__init__(versionhash, language, pdf)
        self.urls = {'regulations': '', 'guidelines': '',
                     'pdf': pdf}
        self.emit_rails_header = False
        self.emit_toc = False
        self.harticle = (u'<div id="{anchor}"></div>'
                         '<h2 id="article-{anchor}-{new}"> '
                         '{name}{sep}{title}'
                         '</h2>\n')
        self.label = (u'<li>[<span class="{name} label label-default">{name}</span>] '
                      '{text}</li>\n')
        self.guideline = (u'<li id="{i}" class="rule">{i}) '
                          '<span class="{label} label {linked}">'
                          '[<a {attr}>{label}</a>]</span> {text}</li>\n')
        # Here we intentionally break the hierarchy (ul(li(ul(li))li()) turns to
        # ul(li()ul(li())li()) to be able to "easily" avoid  page breaking
        # inside a 'li' text (it does weird stuff if the whole element has to
        # avoid page-breaking
        self.regulation = u'<li id="{i}" class="rule">{i}) {text}</li>\n'
        self.postreg = u''
        # Internal variable to handle grouping between a h* and its first element
        self.group_closed = True

    def generate_ul(self, a_list):
        # Here we don't want to generate 'ul' for the root rule, we want to group
        # the first 'li' with the header to force avoiding page-break
        return (len(a_list) > 0 and
                ((isinstance(a_list[0], Rule) and
                  not isinstance(a_list[0].parent, Article)) or
                 isinstance(a_list[0], LabelDecl)))

    def no_break(self):
        if self.group_closed:
            self.group_closed = False
            # This first div will be closed after the first paragraph
            self.codegen += NO_BREAK

    def visitArticle(self, article):
        self.no_break()
        return super(WCADocumentHtmlToPdf, self).visitArticle(article)

    def visitSection(self, section):
        self.no_break()
        return super(WCADocumentHtmlToPdf, self).visitSection(section)

    def visitSubsection(self, subsection):
        self.no_break()
        return super(WCADocumentHtmlToPdf, self).visitSubsection(subsection)

    def visitTableOfContent(self, toc):
        self.no_break()
        return super(WCADocumentHtmlToPdf, self).visitTableOfContent(toc)

    def visitunicode(self, u):
        retval = super(WCADocumentHtmlToPdf, self).visitunicode(u)
        if len(u) > 0 and not self.group_closed:
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
        return super(WCADocumentHtmlToPdf, self).visitRule(rule)

    def visitWCARegulations(self, document):
        self.codegen += '<html><head>'
        self.codegen += '<title>%s</title>' % TITLE
        self.codegen += '<style media="all">\n'
        # Output the font faces for our custom fonts, shipped with the package
        fonts = {'normal': 'cmunrm.otf', 'italic': 'cmunti.otf',
                 'bold': 'cmunbx.otf', 'bi': 'cmunbi.otf'}
        for name in fonts.iterkeys():
            fontfile = pkg_resources.resource_filename("wrc", "data/" + fonts[name])
            if not os.path.isabs(fontfile):
                fontfile = os.path.abspath(fontfile)
            fonts[name] = fontfile
        self.codegen += CSS_FONTS.format(normal=fonts['normal'], bold=fonts['bold'],
                                         italic=fonts['italic'], bi=fonts['bi'])
        self.codegen += pkg_resources.resource_string("wrc", "data/htmltopdf.css").decode("utf-8")
        self.codegen += '</style></head><body class="%s"><div>\n' % self.language
        self.codegen += HTML_TITLE.format(title=TITLE, author=AUTHOR)
        retval = super(WCADocumentHtmlToPdf, self).visitWCARegulations(document)
        self.codegen += '<div class="page_break"></div>\n'
        return retval

    def visitWCAGuidelines(self, document):
        retval = super(WCADocumentHtmlToPdf, self).visitWCAGuidelines(document)
        self.codegen += '</div></body></html>\n'
        return retval
