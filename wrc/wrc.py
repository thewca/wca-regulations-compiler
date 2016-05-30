import argparse
import pkg_resources
import json
import sys
import os
from subprocess import check_call, CalledProcessError
from parse.parser import WCAParser
from sema.ast import WCARegulations, WCAGuidelines
from codegen.html import WCARegulationsHtml, WCAGuidelinesHtml
from codegen.latex import WCADocumentLatex

REGULATIONS_FILENAME = "wca-regulations.md"
GUIDELINES_FILENAME = "wca-guidelines.md"

def parse_regulations_guidelines(reg, guide):
    reg_as_str = None
    guide_as_str = None
    astreg = None
    astguide = None
    errors = []
    warnings = []
    if reg:
        with open(reg) as reg_file:
            reg_as_str = reg_file.read()
        # FIXME: do we want to just remove tabs from regs?
        reg_as_str = reg_as_str.replace("\t", "    ")
    if guide:
        with open(guide) as guide_file:
            guide_as_str = guide_file.read()
        # FIXME: do we want to just remove tabs from regs?
        guide_as_str = guide_as_str.replace("\t", "    ")
    parser = WCAParser()
    if reg_as_str:
        astreg, errors_reg, warnings_reg = parser.parse(reg_as_str, WCARegulations)
        errors.extend(errors_reg)
        warnings.extend(warnings_reg)
    if guide_as_str:
        astguide, errors_guide, warnings_guide = parser.parse(guide_as_str, WCAGuidelines)
        errors.extend(errors_guide)
        warnings.extend(warnings_guide)
    return (astreg, astguide, errors, warnings)

def generate_html(input_regulations, input_guidelines, output_directory, options):
    astreg, astguide, errors, warnings = parse_regulations_guidelines(input_regulations,
                                                                      input_guidelines)
    if len(errors) + len(warnings) == 0 and astreg and astguide:
        print "Compiled Regulations and Guidelines, generating html..."
        cg_reg_html = WCARegulationsHtml(options.version, options.language)
        cg_guide_html = WCAGuidelinesHtml(astreg, options.version, options.language)
        reg_html = cg_reg_html.emit(astreg)
        guide_html = cg_guide_html.emit(astguide)
        if reg_html and guide_html:
            output_reg = output_directory + "/index.html"
            output_guide = output_directory + "/guidelines.html"
            with open(output_reg, 'w+') as f:
                f.write(reg_html)
                print "Successfully written the Regulations' html to " + output_reg
            with open(output_guide, 'w+') as f:
                f.write(guide_html)
                print "Successfully written the Guidelines' html to " + output_guide
        else:
            print "Error: couldn't emit html for Regulations and Guidelines."
            sys.exit(1)
    return (errors, warnings)

def generate_latex(input_regulations, input_guidelines, output_directory, options):
    astreg, astguide, errors, warnings = parse_regulations_guidelines(input_regulations,
                                                                      input_guidelines)
    if len(errors) + len(warnings) == 0 and astreg and astguide:
        print "Compiled Regulations and Guidelines, generating Latex..."

        # Get information about languages from the config file (tex encoding, pdf filename, etc)
        languages_info = json.loads(pkg_resources.resource_string(__name__, "data/languages.json"))

        cglatex = WCADocumentLatex(options.language,
                                   languages_info[options.language]["tex_encoding"])
        latex = cglatex.emit(astreg, astguide)
        if latex:
            base_filename = languages_info[options.language]["pdf"]
            output = output_directory + "/" + base_filename + ".tex"
            with open(output, 'w+') as f:
                f.write(latex)
                print "Successfully written the Latex to " + output
            if options.target == "pdf":
                latex_cmd = [languages_info[options.language]["tex_command"]]
                latex_cmd.append("-output-directory=" + output_directory)
                latex_cmd.append(output_directory + "/" + base_filename + ".tex")
                try:
                    proc = check_call(latex_cmd)
                    # Do it twice for ToC!
                    proc = check_call(latex_cmd)
                    print "Successfully generated pdf file!"
                    print "Cleaning temporary file..."
                    ext_list = [".tex", ".aux", ".log"]
                    for ext in ext_list:
                        to_remove = output_directory + "/" + base_filename + ext
                        print "Removing: " + to_remove
                        os.remove(to_remove)
                except CalledProcessError as err:
                    print "Error while generating pdf:"
                    print err
                    # Removing .aux file to avoid build problem
                    print "Removing .aux file"
                    os.remove(output_directory + "/" + base_filename + ".aux")
                    sys.exit(1)
                except OSError as err:
                    print "Error when running command \"" + " ".join(latex_cmd) + "\""
                    print err
                    sys.exit(1)

        else:
            print "Error: couldn't emit Latex for Regulations and Guidelines."
            sys.exit(1)
    return (errors, warnings)


def run():
    argparser = argparse.ArgumentParser()
    action_group = argparser.add_mutually_exclusive_group()
    action_group.add_argument('--target', help='Select target output kind',
                              choices=['latex', 'pdf', 'html', 'check'])
    action_group.add_argument('--diff', help='Diff against the specified file')
    argparser.add_argument('-o', '--output', default='build/', help='Output directory')
    argparser.add_argument('-l', '--language', default='english', help='Language of the file')
    argparser.add_argument('-v', '--version', default='unknown', help='Git hash corresponding to the files')
    argparser.add_argument('input', help='Input file or directory')


    options = argparser.parse_args()

    input_regulations = None
    input_guidelines = None

    if os.path.isdir(options.input):
        input_regulations = options.input + "/" + REGULATIONS_FILENAME
        input_guidelines = options.input + "/" + GUIDELINES_FILENAME
        if (not os.path.isfile(input_regulations) or
                not os.path.isfile(input_guidelines)):
            print ("Error: the input directory must contain both the Regulations"
                   "and Guidelines files.")
            sys.exit(1)
    elif os.path.isfile(options.input):
        if options.input.endswith(REGULATIONS_FILENAME):
            input_regulations = options.input
        elif options.input.endswith(GUIDELINES_FILENAME):
            input_guidelines = options.input
        else:
            print "Error: couldn't detect if the input file are Regulations or Guidelines."
            sys.exit(1)
    else:
        print "Error: input is not a file or a directory."
        sys.exit(1)

    build_dir = options.output
    if not os.path.isdir(options.output):
        print "Error: output is not a directory."
        sys.exit(1)

    errors = []
    warnings = []


    if not options.diff and not options.target:
        print "Nothing to do, exiting..."
        sys.exit(0)
    if options.diff:
        print "Not supported yet"
        sys.exit(1)
    if options.target == "latex" or options.target == "pdf":
        if not input_regulations or not input_guidelines:
            print ("Error: both the Regulations and Guidelines are needed"
                   "to generate the Latex file.")
            sys.exit(1)
        errors, warnings = generate_latex(input_regulations, input_guidelines, build_dir, options)
    elif options.target == "html":
        if not input_regulations or not input_guidelines:
            print ("Error: both the Regulations and Guidelines are needed"
                   "to generate the Latex file.")
            sys.exit(1)
        errors, warnings = generate_html(input_regulations, input_guidelines, build_dir, options)
    elif options.target == "check":
        astreg, astguide, errors, warnings = parse_regulations_guidelines(input_regulations,
                                                                          input_guidelines)
        if len(errors) + len(warnings) == 0:
            print "All checks passed !"

    # If some errors or warnings have been detected, output them
    if len(errors) + len(warnings) != 0:
        print "Couldn't compile file, the following occured:"
        for e in errors:
            print " - Error: " + e
        for w in warnings:
            print " - Warning: " + w
        sys.exit(1)

if __name__ == '__main__':
    run()
