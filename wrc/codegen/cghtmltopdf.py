import re
import pkg_resources
from wrc.sema.ast import WCAGuidelines, WCARegulations, Ruleset,\
                     Rule, LabelDecl
from wrc.codegen.cghtml import WCADocumentHtml
from wrc.codegen.cg import CGDocument

# TODO
# fusionner
# renommer ancre articles
# parametrer la creation de lien


class WCADocumentHtmlToPdf(WCADocumentHtml):
    def __init__(self, versionhash, language, pdf):
        super(WCADocumentHtmlToPdf, self).__init__(versionhash, language, pdf)

    def emit(self, astreg, astguide):
        pass
        # cgreg = WCARegulationsHtml(self.versionhash, self.language)
        # result = cgreg.emit(astreg)
        # cgguide = WCAGuidelinesHtml(astreg, self.versionhash, self.language)
        # result_guide = cgguide.emit(astguide)
        # retval = '<html><head>'
        # retval += ('<style>%s</style>' %
                   # pkg_resources.resource_string("wrc", "data/htmltopdf.css"))
        # retval += '</head><body>%s</body></html>' % (result +
                                                     # '<div class="page_break"></div>' +
                                                     # result_guide)
        # return retval


