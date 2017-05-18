import argparse
import json
import sys
import os
from subprocess import check_call, CalledProcessError
import pkg_resources
from .parse.parser import WCAParser
from .sema.ast import WCARegulations, WCAGuidelines, WCAStates, Ruleset
from .codegen.cghtml import WCADocumentHtml
from .codegen.cghtmltopdf import WCADocumentHtmlToPdf
from .codegen.cgjson import WCADocumentJSON
from .version import __version__

REGULATIONS_FILENAME = "wca-regulations.md"
GUIDELINES_FILENAME = "wca-guidelines.md"
STATES_FILENAME = "wca-states.md"

def parse_states(states):
    states_as_str = None
    astreg = None
    errors = []
    warnings = []
    if states:
        with open(states) as states_file:
            states_as_str = states_file.read()
    parser = WCAParser()
    if states_as_str:
        astreg, errors, warnings = parser.parse(states_as_str, WCAStates)
    return (astreg, None, errors, warnings)

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

def output(result_tuple, outputs, output_dir):
    output_filename = None
    for content, filename in zip(result_tuple, outputs):
        mode = 'w'
        if output_filename == output_dir + "/" + filename:
            mode = 'a'
        else:
            output_filename = output_dir + "/" + filename
        with open(output_filename, mode + '+') as output_file:
            output_file.write(content)
            print "Successfully written the content to " + output_filename

def generate(backend_class, inputs, outputs, options, parsing_method, post_process=None):
    astreg, astguide, errors, warnings = parsing_method(*inputs)
    if len(errors) + len(warnings) == 0:
        print ("Compiled document, generating " +
               backend_class.name + "...")
        languages_options = languages(False)[options.language]
        cg_instance = backend_class(options.git_hash, options.language,
                                    languages_options["pdf"])
        result_tuple = cg_instance.emit(astreg, astguide)
        output(result_tuple, outputs, options.output)
        if post_process:
            post_process(outputs, options.output, languages_options)
    return (errors, warnings)

def html_to_pdf(tmp_filenames, output_directory, lang_options):
    input_html = output_directory + "/" + tmp_filenames[0]
    wkthml_cmd = ["wkhtmltopdf"]
    # Basic margins etc
    wkthml_cmd.extend(["--margin-left", "18"])
    wkthml_cmd.extend(["--margin-right", "18"])
    wkthml_cmd.extend(["--page-size", "Letter"])
    # Header and Footer
    header_file = pkg_resources.resource_filename("wrc", "data/header.html")
    footer_file = pkg_resources.resource_filename("wrc", "data/footer.html")
    wkthml_cmd.extend(["--header-html", header_file])
    wkthml_cmd.extend(["--footer-html", footer_file])
    wkthml_cmd.extend(["--header-spacing", "8"])
    wkthml_cmd.extend(["--footer-spacing", "8"])
    wkthml_cmd.append(input_html)
    wkthml_cmd.append(output_directory + "/" + lang_options['pdf'] + '.pdf')
    try:
        check_call(wkthml_cmd)
        print "Successfully generated pdf file!"
        print "Cleaning temporary file (%s)..." % input_html
        os.remove(input_html)
    except CalledProcessError as err:
        print "Error while generating pdf:"
        print err
        sys.exit(1)
    except OSError as err:
        print "Error when running command \"" + " ".join(wkthml_cmd) + "\""
        print err
        sys.exit(1)

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

def check_states_file(file_or_directory):
    if not os.path.isfile(file_or_directory) or not file_or_directory.endswith(STATES_FILENAME):
        print "Error: input file is not as expected.."
        sys.exit(1)

def build_common_option(argparser):
    argparser.add_argument('-o', '--output', default='build/', help='Output directory')
    argparser.add_argument('input', help='Input file or directory')
    argparser.add_argument('-g', '--git-hash', default='unknown',
                           help='Git hash corresponding to the files')
    argparser.add_argument('-l', '--language', default='english', help='Language of the file')

def handle_errors_and_warnings(errors, warnings):
    # If some errors or warnings have been detected, output them
    if len(errors) + len(warnings) != 0:
        print "Couldn't compile file, the following occured:"
        for err in errors:
            print " - Error: " + err
        for warn in warnings:
            print " - Warning: " + warn
        sys.exit(1)

def states():
    argparser = argparse.ArgumentParser()
    build_common_option(argparser)
    argparser.add_argument('--target', help='Select target output kind',
                           choices=['check', 'json'])
    options = argparser.parse_args()

    check_states_file(options.input)

    if options.target == "json":
        check_output(options.output)
        errors, warnings = generate(WCADocumentJSON,
                                    [options.input],
                                    ["states.json"],
                                    options,
                                    parse_states)
    elif options.target == "check":
        print "Checking input file(s)..."
        astreg, astguide, errors, warnings = parse_states(options.input)
        if len(errors) + len(warnings) == 0:
            print "All checks passed!"
    else:
        print "Nothing to do, exiting..."
        sys.exit(0)

    handle_errors_and_warnings(errors, warnings)

def run():
    argparser = argparse.ArgumentParser()
    action_group = argparser.add_mutually_exclusive_group()
    action_group.add_argument('--target', help='Select target output kind',
                              choices=['latex', 'pdf', 'html', 'check',
                                       'json'])
    action_group.add_argument('--diff', help='Diff against the specified file')
    action_group.add_argument('-v', '--version', action='version',
                              version=__version__)
    build_common_option(argparser)

    options = argparser.parse_args()

    if not options.diff and not options.target:
        print "Nothing to do, exiting..."
        sys.exit(0)

    input_regulations, input_guidelines = files_from_dir(options.input)

    errors = []
    warnings = []

    if options.target == "html":
        check_output(options.output)
        errors, warnings = generate(WCADocumentHtml,
                                    (input_regulations, input_guidelines),
                                    ["index.html.erb", "guidelines.html.erb"],
                                    options, parse_regulations_guidelines)
    elif options.target == "pdf":
        check_output(options.output)
        if not input_regulations or not input_guidelines:
            print ("Error: both the Regulations and Guidelines are needed "
                   "to generate the pdf file.")
            sys.exit(1)
        errors, warnings = generate(WCADocumentHtmlToPdf,
                                    (input_regulations, input_guidelines),
                                    ["regulations_tmp.html", "regulations_tmp.html"],
                                    options, parse_regulations_guidelines,
                                    html_to_pdf)
        # errors, warnings = generate_htmltopdf(input_regulations, input_guidelines, options)
    elif options.target == "json":
        check_output(options.output)
        errors, warnings = generate(WCADocumentJSON,
                                    (input_regulations, input_guidelines),
                                    ["wca-regulations.json"],
                                    options, parse_regulations_guidelines)
    elif options.target == "check" or options.diff:
        print "Checking input file(s)..."
        astreg, astguide, errors, warnings = parse_regulations_guidelines(input_regulations,
                                                                          input_guidelines)
        if len(errors) + len(warnings) == 0:
            print "All checks passed!"
            if options.diff:
                print "Checking reference file(s) for diff"
                errors, warnings = generate_diff(astreg, astguide, options)

    handle_errors_and_warnings(errors, warnings)

if __name__ == '__main__':
    run()
