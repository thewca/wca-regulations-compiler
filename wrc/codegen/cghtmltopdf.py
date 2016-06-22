# import re
import pkg_resources
import os.path
# from wrc.sema.ast import WCAGuidelines, WCARegulations, Ruleset,\
                     # Rule, LabelDecl
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
HTML_TITLE = '<div class="title">{title}</div><div class="author">{author}</div>'


class WCADocumentHtmlToPdf(WCADocumentHtml):
    def __init__(self, versionhash, language, pdf):
        super(WCADocumentHtmlToPdf, self).__init__(versionhash, language, pdf)
        self.urls = {'regulations': '', 'guidelines': '',
                     'pdf': pdf}
        self.emit_rails_header = False
        self.emit_toc = False
        self.harticle = (u'<div id="{anchor}"></div>'
                          '<h2 id="article-{anchor}-{new}" class="article"> '
                          '{name}{sep}{title}'
                          '</h2>\n')
        self.label = (u'<li>[<span class="{name} label label-default">{name}</span>] '
                       '{text}</li>\n')
        self.guideline = (u'<li id="{i}">{i}) '
                           '<span class="{label} label {linked}">'
                           '[<a {attr}>{label}</a>]</span> {text}</li>\n')
        # Here we intentionally break the hierarchy (ul(li(ul(li))li()) turns to
        # ul(li()ul(li())li()) to be able to "easily" avoid  page breaking
        # inside a 'li' text (it does weird stuff if the whole element has to
        # avoid page-breaking
        self.regulation = u'<li id="{i}">{i}) {text}</li>'
        self.postreg = u''

    def visitWCARegulations(self, document):
        self.codegen += '<html><head>'
        self.codegen += '<title>%s</title>' % TITLE
        self.codegen += '<style>\n'
        fonts = {'normal': 'cmunrm.otf', 'italic': 'cmunti.otf',
                 'bold': 'cmunbx.otf', 'bi': 'cmunbi.otf'}
        for name in fonts.iterkeys():
            fontfile = pkg_resources.resource_filename("wrc", "data/" + fonts[name])
            if not os.path.isabs(fontfile):
                fontfile = os.path.abspath(fontfile)
            fonts[name] = fontfile
        self.codegen += CSS_FONTS.format(normal=fonts['normal'], bold=fonts['bold'],
                                         italic=fonts['italic'], bi=fonts['bi']);
        self.codegen += pkg_resources.resource_string("wrc", "data/htmltopdf.css")
        self.codegen += '</style></head><body><div>\n'
        self.codegen += HTML_TITLE.format(title=TITLE, author=AUTHOR)
        retval = super(WCADocumentHtmlToPdf, self).visitWCARegulations(document)
        self.codegen += '<div class="page_break"></div>\n'
        return retval

    def visitWCAGuidelines(self, document):
        retval = super(WCADocumentHtmlToPdf, self).visitWCAGuidelines(document)
        self.codegen += '</div></body></html>\n'
        return retval
