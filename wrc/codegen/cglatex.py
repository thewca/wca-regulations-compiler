import re
from wrc.sema.ast import WCADocument, WCARegulations, Ruleset,\
                     Rule, LabelDecl
from wrc.codegen.cg import CGDocument

PDF_LINK = "wca-regulations-and-guidelines.pdf"
H2 = u'\\subsection{{{title}}}\\label{{{anchor}}}\n'
H3 = u'\\subsubsection{{{title}}}\\label{{{anchor}}}\n'
TITLE = u'\\section{{{title}}}\\label{{{anchor}-top}}\n'

GUIDELINE = u'\\item \\label{{{i}}}\n {i}) [{label}] {text}\n'
LABEL = u'\\item\n {{[}}{{{name}}}{{]}} {{{text}}}\n'
REGULATION = u'\\item \\label{{{i}}} {i}) {text}\n'

CLASS = u"\\documentclass[12pt]{article}"

HEADER = """\\usepackage[top=2cm, bottom=2cm, left=2cm, right=2cm]{geometry}
\\usepackage[bookmarksopen=true]{hyperref}
\\hypersetup{pdfborderstyle={/S/U/W 1},pdfborder=0 0 1}

\\usepackage{bookmark}

\\usepackage{fancyhdr}
\\pagestyle{fancy}

\\setcounter{secnumdepth}{-1}

\\providecommand{\\tightlist}{%
  \\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}

\\title{WCA Regulations and Guidelines}
\\author{WCA Regulations Committee}
\\date{\\vspace{-1em}}

\\begin{document}

\\maketitle\n"""

BREAK = """\\newpage"""
FOOTER = """\\end{document}"""

ENCODING = {"default": [],
            "cjk": ["\\usepackage{xeCJK}", "\\setCJKmainfont{AR PL UMing CN}"],
            "hungarian": ["\\usepackage[magyar]{babel}",
                          "\\usepackage[T1]{fontenc}",
                          "\\usepackage[utf8x]{inputenc}"],
            "korean": ["\\usepackage[fallback]{xeCJK}",
                       "\\usepackage{fontspec}",
                       "\\setCJKmainfont{UnBatang}"],
            "russian": ["\\usepackage[utf8]{inputenc}", "\\usepackage[russian]{babel}"],
            "french": ["\\usepackage[french]{babel}",
                       "\\usepackage[T1]{fontenc}",
                       "\\usepackage[utf8]{inputenc}"],
            "utf8": ["\\usepackage[utf8]{inputenc}"]
           }

# Some homemade basics non-robust md2latex functions
# We could also call pandoc to do the conversion but it's awfully slow

def anchorizer(text):
    accepted = re.compile(r'[\W_ ]+')
    text = accepted.sub('', text)
    if len(text) == 0:
        text = "0"
    return text.lower().replace(" ", "-")


def special_links_replace(text):
    regOrGuide2Slots = r'([A-Za-z0-9]+)' + r'(\+*)'
    regsURL = "wca-regulations"
    guidesURL = "wca-guidelines"
    # FIXME: Instead of doing this dirty replacement we could just make the
    # regulations and guidelines labels be 'regulations:regulation:thing'!
    reference_list = [(r'regulations:article:' + regOrGuide2Slots, "reg-"),
                      (r'regulations:regulation:' + regOrGuide2Slots, ""),
                      (r'guidelines:article:' + regOrGuide2Slots, "guide-"),
                      (r'guidelines:guideline:' + regOrGuide2Slots, ""),
                     ]
    # FIXME: same here
    anchor_list = [(r'regulations:contents', regsURL + "-contents"),
                   (r'guidelines:contents', guidesURL + "-contents"),
                   (r'regulations:top', regsURL + "-top"),
                   (r'guidelines:top', guidesURL + "-top"),
                   # FIXME: very ugly (why do we even bother, they are reading it!)
                   (r'link:pdf', WCADocumentLatex.root_pdf + PDF_LINK),
                  ]
    retval = text
    for match, repl in reference_list:
        retval = re.sub(match, repl + r'\1\2', retval)
    for match, repl in anchor_list:
        retval = re.sub(match, repl, retval)
    return retval

def link2latex(text):
    match = r'\[([^\]]+)\]\((?!regulations|guidelines)([^)]+)\)'
    replace = r'\href{\2}{\1}'
    return re.sub(match, replace, text)

def anchorlink2latex(text):
    match = r'\[([^\]]+)\]\(([^)]+)\)'
    replace = r'\hyperref[\2]{\1}'
    return re.sub(match, replace, text)

def simple_md2latex(text):
    # We want to escape '#', '{', '}' as they are special chars for Latex
    text = re.sub(r'([{}#])', r'\\\1', text)
    # LaTeX will render two dashes as an em hyphen.
    # This regex replacement makes sure Megaminx notation is rendered correctly.
    text = re.sub(r'--', r'-{}-', text)
    # Convert non trailing newlines to break in paragraph
    text = re.sub(r'\n(?=.)', r'\\\\\n', text)
    text = link2latex(text)
    text = special_links_replace(text)
    return anchorlink2latex(text)


class WCADocumentLatex(CGDocument):
    root_pdf = ""
    def __init__(self, language, encoding):
        super(WCADocumentLatex, self).__init__()
        self.codegen = u""
        self.codegen = u"\n".join([CLASS,
                                   "\n".join(ENCODING[encoding]),
                                   HEADER])
        # This CG can handle both
        self.doctype = WCADocument
        self.regset = []
        self.current = None
        online_url = "https://www.worldcubeassociation.org/regulations/"
        if language != "english":
            online_url += "translations/" + language
        WCADocumentLatex.root_pdf = online_url

    def emit(self, regulations, guidelines):
        # FIXME: this override a function with a different number of arguments,
        # this is bad
        self.regset = Ruleset().get(regulations)
        retval = self.visit(regulations)
        self.codegen += BREAK
        retval = retval and self.visit(guidelines)
        self.codegen += FOOTER
        return self.codegen.encode("utf8")

    def visitWCADocument(self, document):
        self.current = document.__class__
        self.codegen += TITLE.format(anchor=anchorizer(document.title),
                                     title=document.title)
        self.codegen += document.version + "\n"
        retval = [self.visit(s) for s in document.sections]
        return retval.count(False) == 0

    def visitlist(self, o):
        genul = len(o) > 0 and (isinstance(o[0], Rule) or isinstance(o[0], LabelDecl))
        if genul:
            self.codegen += "\n\\begin{itemize}\n\\tightlist\n"
        retval = super(WCADocumentLatex, self).visitlist(o)
        if genul:
            self.codegen += "\\end{itemize}\n"
        return retval

    def visitunicode(self, u):
        if len(u) > 0:
            self.codegen += simple_md2latex(u) + "\n"
        return True

    def visitTableOfContent(self, toc):
        # Remove the contents tag from the title
        title = re.sub(r'<contents>\s*', r'', toc.title)
        prefix = "wca-regulations-" if self.current == WCARegulations else "wca-guidelines-"
        self.codegen += H2.format(anchor=prefix + "contents",
                                  title=simple_md2latex(title))
        retval = super(WCADocumentLatex, self).visit(toc.intro)
        # FIXME: do we want to output an actual table of content?
        return retval

    def visitSection(self, section):
        self.codegen += H2.format(anchor=anchorizer(section.title),
                                  title=section.title)
        return super(WCADocumentLatex, self).visitSection(section)

    def visitArticle(self, article):
        prefix = "reg-" if self.current == WCARegulations else "guide-"
        self.codegen += H2.format(anchor=prefix + article.number,
                                  title=article.sep.join([article.name,
                                                          article.title]))
        retval = super(WCADocumentLatex, self).visit(article.intro)
        retval = retval and super(WCADocumentLatex, self).visit(article.content)
        return retval

    def visitSubsection(self, subsection):
        self.codegen += H3.format(anchor=anchorizer(subsection.title),
                                  title=subsection.title)
        return super(WCADocumentLatex, self).visitSubsection(subsection)

    def visitRegulation(self, reg):
        self.codegen += REGULATION.format(i=reg.number,
                                          text=simple_md2latex(reg.text))
        retval = super(WCADocumentLatex, self).visitRegulation(reg)
        return retval

    def visitLabelDecl(self, decl):
        self.codegen += LABEL.format(name=decl.name, text=decl.text)
        return True

    def visitGuideline(self, guide):
        reg = guide.regname
        if reg in self.regset:
            label = "\\hyperref[%s]{%s}" % (reg, guide.labelname)
        else:
            label = guide.labelname

        self.codegen += GUIDELINE.format(i=guide.number,
                                         text=simple_md2latex(guide.text),
                                         label=label)
        return True


