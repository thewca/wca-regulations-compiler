from wrc.sema.ast import Article, Section, TableOfContent, split_rule_number

NOTES_INDEX = 0
TOC_INDEX = 1
FIRST_ARTICLE_INDEX = 2


class BadFormatError(Exception):
    def __init__(self, message: str):
        self.message = message + '. Please report this issue to the developer.'
        super().__init__(message)


def compare_article_numbers(num1: str, num2: str) -> bool:
    """
    Returns True if num1 < num2. Otherwise returns False.
    This is necessary because:
    * We need to compare article numbers like '1' and 'A'.
    * '2' > '10' == True, which is a problem.
    """
    is_digit_1 = num1.isdigit()
    is_digit_2 = num2.isdigit()
    if is_digit_1 and is_digit_2:
        res = int(num1) < int(num2)
    elif is_digit_1 and not is_digit_2:
        # Only num2 is a letter.
        res = True
    elif not is_digit_1 and not is_digit_2:
        res = num1 < num2
    else:
        res = False

    return res


def compare_reg_numbers(num1: str, num2: str) -> bool:
    """
    Returns True if num1 < num2, otherwise returns False.
    We need this for the same reasons we need compare_article_numbers().
    Here we use the split_rule_number function to split the numbers into lists.
    """
    num1 = split_rule_number(num1)
    num2 = split_rule_number(num2)
    for n1, n2 in zip(num1, num2):
        if n1 < n2:
            return True
        elif n1 > n2:
            return False

    return len(num1) < len(num2)


def merge_ast(astreg, astguide, language_options):
    """
    Combine the two AST into one.
    """
    # We only want the Articles, so we will start the for loop below at FIRST_ARTICLE_INDEX,
    # and check if the indices for Notes, TOC and First Article are correct.
    if not isinstance(astreg.sections[NOTES_INDEX], Section) or \
            not isinstance(astguide.sections[NOTES_INDEX], Section):
        raise BadFormatError('NOTES_INDEX is incorrect')
    if not isinstance(astreg.sections[TOC_INDEX], TableOfContent):
        raise BadFormatError('TOC_INDEX is incorrect')
    if not (hasattr(astreg.sections[FIRST_ARTICLE_INDEX], 'number') and astreg.sections[
                FIRST_ARTICLE_INDEX].number == '1'):
        raise BadFormatError('FIRST_ARTICLE_INDEX is incorrect.')

    ast_combined = astreg

    # Merge the notes.
    # We won't include the "WCA Regulations" notes from the Guidelines, as it is the same as in
    # "WCA Regulations and Guidelines" of the Regulations document.
    ast_combined.sections[NOTES_INDEX].content.append(
        [cont for cont in astguide.sections[NOTES_INDEX].content if language_options['regulations'] not in cont.title])

    for guide_section in astguide.sections[FIRST_ARTICLE_INDEX:]:

        stack = guide_section.content
        reg_section = None
        # Find the associated section in the Regulations or add it if there isn't one.
        for index, section in enumerate(ast_combined.sections[FIRST_ARTICLE_INDEX:]):
            if not isinstance(section, Article):
                raise BadFormatError('Section is not an Article.')
            if section.number == guide_section.number:
                reg_section = section
                break
            elif compare_article_numbers(guide_section.number, section.number):
                # This happens when an Article in the Guidelines doesn't have an associated article in the Regulations.
                ast_combined.sections[TOC_INDEX].articles.insert(index, guide_section)
                # Now we copy the Article from the Guidelines into the ast_combined and continue (empty stack).
                ast_combined.sections.insert(index + FIRST_ARTICLE_INDEX, guide_section)
                stack = []
                break

        while len(stack) > 0:
            guideline = stack.pop(0)
            guideline_num = guideline.number.split('+')[0]
            if guideline_num == 'A7g+':
                print("Here.")
            recursive_insert(reg_section.content, guideline, guideline_num, stack)

    return ast_combined


def recursive_insert(root, guideline, guideline_num, stack) -> int:
    """
    Insert guideline with a recursive algorithm.
    guideline_num: number of the guideline without the '+'.
    """
    inserted_index = -1  # We use this as a flag and as an auxiliary variable to manipulate index.
    for index, node in enumerate(root):
        if inserted_index >= 0:
            inserted_index = index
            break
        if len(node.number) == len(guideline_num) and not compare_reg_numbers(node.number, guideline_num):
            if node.number == guideline_num:
                inserted_index = index + 1
            elif compare_reg_numbers(guideline_num, node.number):
                # When the guideline does not have an associated regulation.
                inserted_index = index
            root.insert(inserted_index, guideline)
            while len(stack) > 0 and stack[0].number.split('+')[0] == guideline_num:
                plus_guideline = stack.pop(0)
                if plus_guideline.number == 'A7g+':
                    print("Here.")
                inserted_index += 1
                root.insert(inserted_index, plus_guideline)
            # Now we move the children of the affected Regulation to the children of the last Guideline added
            # for such Regulation.
            root[inserted_index].children = node.children
            node.children = []
            break

        elif len(node.number) < len(guideline_num) and node.number == guideline_num[:len(node.number)]:
            # Go down.
            inserted_index = recursive_insert(node.children, guideline, guideline_num, stack)
        # else: continue for.

    return inserted_index
