import argparse
import json
import sys
import os
from subprocess import check_call, CalledProcessError
import pkg_resources
from .parse.parser import WCAParser
from .sema.ast import WCARegulations, WCAGuidelines, Ruleset
from .codegen.html import WCARegulationsHtml, WCAGuidelinesHtml
from .codegen.latex import WCADocumentLatex

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

def generate_html(input_regulations, input_guidelines, options):
    output_directory = options.output
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
            with open(output_reg, 'w+') as output_file:
                output_file.write(reg_html)
                print "Successfully written the Regulations' html to " + output_reg
            with open(output_guide, 'w+') as output_file:
                output_file.write(guide_html)
                print "Successfully written the Guidelines' html to " + output_guide
        else:
            print "Error: couldn't emit html for Regulations and Guidelines."
            sys.exit(1)
    return (errors, warnings)

def generate_latex(input_regulations, input_guidelines, options):
    output_directory = options.output
    astreg, astguide, errors, warnings = parse_regulations_guidelines(input_regulations,
                                                                      input_guidelines)
    if len(errors) + len(warnings) == 0 and astreg and astguide:
        print "Compiled Regulations and Guidelines, generating Latex..."

        languages_info = languages(False)

        cglatex = WCADocumentLatex(options.language,
                                   languages_info[options.language]["tex_encoding"])
        latex = cglatex.emit(astreg, astguide)
        if latex:
            base_filename = languages_info[options.language]["pdf"]
            output = output_directory + "/" + base_filename + ".tex"
            with open(output, 'w+') as output_file:
                output_file.write(latex)
                print "Successfully written the Latex to " + output
            if options.target == "pdf":
                latex_cmd = [languages_info[options.language]["tex_command"]]
                latex_cmd.append("-output-directory=" + output_directory)
                latex_cmd.append(output_directory + "/" + base_filename + ".tex")
                try:
                    check_call(latex_cmd)
                    # Do it twice for ToC and ref!
                    print "Running second pass silently."
                    devnull = open(os.devnull, 'w')
                    check_call(latex_cmd, stdout=devnull)
                    print "Successfully generated pdf file!"
                    print "Cleaning temporary file..."
                    for ext in [".tex", ".aux", ".log"]:
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

def output_diff(submitted, reference):
    rules_visitor = Ruleset()
    set_submitted = rules_visitor.get(submitted)
    set_reference = rules_visitor.get(reference)
    unexpected = set_submitted - set_reference
    missing = set_reference - set_submitted
    if len(unexpected) > 0:
        print ("/!\\ These numbers are in the translation file, "
               "but not in the reference one: {%s}" % ', '.join(sorted(unexpected)))
    if len(missing) > 0:
        print ("/!\\ These numbers are in the reference file, "
               "but not in the translation one: {%s}" % ', '.join(sorted(missing)))
    return len(unexpected) + len(missing)

def generate_diff(input_ast_reg, input_ast_guide, options):
    ref_regulations, ref_guidelines = files_from_dir(options.diff)
    parse_ref = parse_regulations_guidelines(ref_regulations, ref_guidelines)
    astreg_ref, astguide_ref, errors, warnings = parse_ref
    if len(errors) + len(warnings) != 0:
        print "Couldn't compile reference Regulations and Guidelines"
    else:
        print "All checks passed!"
        diffs = 0
        if input_ast_reg and astreg_ref:
            diffs += output_diff(input_ast_reg, astreg_ref)
        elif input_ast_reg:
            print "No reference to compare the intput Regulations to"

        if input_ast_guide and astguide_ref:
            diffs += output_diff(input_ast_guide, astguide_ref)
        elif input_ast_guide:
            print "No reference to compare the input Guidelines to"
        if diffs == 0:
            print "Input file(s) and reference file(s) matched!"
        else:
            errors.append("Translation and reference did not match!")
    return (errors, warnings)


def files_from_dir(file_or_directory):
    regulations = None
    guidelines = None
    if os.path.isdir(file_or_directory):
        regulations = file_or_directory + "/" + REGULATIONS_FILENAME
        guidelines = file_or_directory + "/" + GUIDELINES_FILENAME
        if (not os.path.isfile(regulations) or
                not os.path.isfile(guidelines)):
            print ("Error: the directory '%s' must contain both the Regulations "
                   "and Guidelines files." % file_or_directory)
            sys.exit(1)
    elif os.path.isfile(file_or_directory):
        if file_or_directory.endswith(REGULATIONS_FILENAME):
            regulations = file_or_directory
        elif file_or_directory.endswith(GUIDELINES_FILENAME):
            guidelines = file_or_directory
        else:
            print "Error: couldn't detect if the input file are Regulations or Guidelines."
            sys.exit(1)
    else:
        print "Error: %s is not a file or a directory." % file_or_directory
        sys.exit(1)
    return (regulations, guidelines)

def check_output(directory):
    if not os.path.isdir(directory):
        print "Error: output is not a directory."
        sys.exit(1)

def languages(display=True):
    # Get information about languages from the config file (tex encoding, pdf filename, etc)
    languages_info = json.loads(pkg_resources.resource_string(__name__, "data/languages.json"))

    if display:
        print " ".join([key for key in languages_info.keys() if key != "english"])
        sys.exit(0)
    return languages_info

def run():
    argparser = argparse.ArgumentParser()
    action_group = argparser.add_mutually_exclusive_group()
    action_group.add_argument('--target', help='Select target output kind',
                              choices=['latex', 'pdf', 'html', 'check'])
    action_group.add_argument('--diff', help='Diff against the specified file')
    argparser.add_argument('-o', '--output', default='build/', help='Output directory')
    argparser.add_argument('-l', '--language', default='english', help='Language of the file')
    argparser.add_argument('-v', '--version', default='unknown',
                           help='Git hash corresponding to the files')
    argparser.add_argument('input', help='Input file or directory')


    options = argparser.parse_args()

    input_regulations, input_guidelines = files_from_dir(options.input)

    errors = []
    warnings = []


    if not options.diff and not options.target:
        print "Nothing to do, exiting..."
        sys.exit(0)

    if options.target == "latex" or options.target == "pdf":
        check_output(options.output)
        if not input_regulations or not input_guidelines:
            print ("Error: both the Regulations and Guidelines are needed "
                   "to generate the Latex file.")
            sys.exit(1)
        errors, warnings = generate_latex(input_regulations, input_guidelines, options)
    elif options.target == "html":
        check_output(options.output)
        if not input_regulations or not input_guidelines:
            print ("Error: both the Regulations and Guidelines are needed "
                   "to generate the html file.")
            sys.exit(1)
        errors, warnings = generate_html(input_regulations, input_guidelines, options)
    elif options.target == "check" or options.diff:
        print "Checking input file(s)..."
        astreg, astguide, errors, warnings = parse_regulations_guidelines(input_regulations,
                                                                          input_guidelines)
        if len(errors) + len(warnings) == 0:
            print "All checks passed!"
            if options.diff:
                print "Checking reference file(s) for diff"
                errors, warnings = generate_diff(astreg, astguide, options)


    # If some errors or warnings have been detected, output them
    if len(errors) + len(warnings) != 0:
        print "Couldn't compile file, the following occured:"
        for err in errors:
            print " - Error: " + err
        for warn in warnings:
            print " - Warning: " + warn
        sys.exit(1)

if __name__ == '__main__':
    run()
