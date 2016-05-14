from parse.parser import WCAParser
from sema.ast import WCARegulations, WCAGuidelines
from codegen.html import WCARegulationsHtml, WCAGuidelinesHtml

PREFIX="example/"
VERSION="67444fd"

with open(PREFIX + 'wca-guidelines.md') as f:
    dataguide = f.read()

with open(PREFIX + 'wca-regulations.md') as f:
    datareg = f.read()
    # Required to have some translations compile
    # datareg = datareg.replace("\t", "    ")

parser = WCAParser()

astreg, errors, warnings = parser.parse(datareg, WCARegulations)
if len(errors) + len(warnings) == 0:
    print "Regulations compiled successfully"
    cghtml = WCARegulationsHtml(VERSION)
    html = cghtml.emit(astreg)
    if html:
        with open(PREFIX + 'index.html', 'w+') as f:
            f.write(html)
else:
    print "Couldn't compile Regulations:"
for e in errors:
    print " - Error: " + e
for w in warnings:
    print " - Warning: " + w

astguide, errors, warnings = parser.parse(dataguide, WCAGuidelines)
if len(errors) + len(warnings) == 0:
    print "Guidelines compiled successfully"
    if astreg:
        cghtml = WCAGuidelinesHtml(astreg, VERSION)
        html = cghtml.emit(astguide)
        if html:
            with open(PREFIX + 'guidelines.html', 'w+') as f:
                f.write(html)
    else:
        print "Cannot generate guidelines: regulations AST is None"
else:
    print "Couldn't compile Guidelines:"
for e in errors:
    print " - Error: " + e
for w in warnings:
    print " - Warning: " + w

