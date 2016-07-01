''' Backend for JSON.  '''
import json
from wrc.sema.ast import WCADocument, Guideline
from wrc.codegen.cg import CGDocument
from wrc.codegen.cghtml import simple_md2html

REGULATIONS_ROOT = "https://www.worldcubeassociation.org/regulations/"


class WCADocumentJSON(CGDocument):
    ''' Implement a simple JSON generator from Regulations and Guidelines ASTs. '''

    name = "JSON"
    def __init__(self, versionhash, language, pdf):
        # We don't need them
        del versionhash, language
        super(WCADocumentJSON, self).__init__(list)
        self.urls = {'regulations': REGULATIONS_ROOT,
                     'guidelines': REGULATIONS_ROOT + "guidelines.html",
                     'pdf': pdf}

    def emit(self, regulations, guidelines):
        reg_list, guide_list = super(WCADocumentJSON, self).emit(regulations, guidelines)
        reg_list.extend(guide_list)
        return json.dumps(reg_list), ""


    def visitRule(self, reg):
        url = "/regulations/"
        if isinstance(reg, Guideline):
            url += "guidelines.html"
        url += "#" + reg.number
        self.codegen.append({'class': 'regulation', 'id': reg.number,
                             'text': simple_md2html(reg.text, self.urls),
                             'url': url})
        retval = super(WCADocumentJSON, self).visitRule(reg)
        return retval

