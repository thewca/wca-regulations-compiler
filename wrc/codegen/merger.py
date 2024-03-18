from wrc.sema.ast import Article, Section, TableOfContent, Guideline, split_rule_number
from copy import deepcopy

NOTES_INDEX = 0
TOC_INDEX = 1
FIRST_ARTICLE_INDEX = 2


class BadFormatError(Exception):
    def __init__(self, message: str):
        self.message = message + '. Please report this issue to the developer.'
        super().__init__(message)


def compare_article_numbers(num1: str, num2: str) -> bool:
    """
    Returns True if num1 < num2, otherwise returns False.
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


def compare_reg_numbers(num1: list, num2: list) -> bool:
    """
    Returns True if num1 < num2, otherwise returns False.
    We need this for the same reasons we need compare_article_numbers().
    """
    for n1, n2 in zip(num1, num2):
        if n1 < n2:
            return True
        elif n1 > n2:
            return False

    return len(num1) < len(num2)


def get_reg_number(reg):
    if isinstance(reg, Guideline):
        reg = reg.number.split('+')[0]
        num = split_rule_number(reg)
    else:
        num = split_rule_number(reg.number)
    if str(num[-1]) == '0':
        # Because split_rule_number() sometimes returns a 0 at the end, and we don't want that here.
        del num[-1]
    return num


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

    # We take the astreg as the base, and then we add the guidelines in their corresponding places.
    ast_combined = astreg

    # Merge the notes:
    # We won't include the "WCA Regulations" notes from the Guidelines, as it is the same as in
    # "WCA Regulations and Guidelines" of the Regulations document.
    # languages_options is used to handle translations.
    ast_combined.sections[NOTES_INDEX].content.append(
        [cont for cont in astguide.sections[NOTES_INDEX].content if language_options['regulations'] not in cont.title])

    # Now we iterate over all the Articles found in astguide, starting from FIRST_ARTICLE_INDEX.
    for guide_section in astguide.sections[FIRST_ARTICLE_INDEX:]:

        stack = deepcopy(guide_section.content)
        reg_section = None
        # Find the associated section in the Regulations or add it if there isn't one.
        for index, section in enumerate(ast_combined.sections[FIRST_ARTICLE_INDEX:]):
            if not isinstance(section, Article):
                # We could just continue here, but finding a non-Article section after FIRST_ARTICLE_INDEX
                # is worth raising an exception.
                raise BadFormatError('Section is not an Article.')

            if section.number == guide_section.number:
                # We found the section!
                reg_section = section
                break
            elif compare_article_numbers(guide_section.number, section.number):
                # This happens when an Article in the Guidelines doesn't have an associated article in the Regulations.
                ast_combined.sections[TOC_INDEX].articles.insert(index, guide_section)
                # Now we copy the Article from the Guidelines into the ast_combined and continue (empty stack).
                ast_combined.sections.insert(index + FIRST_ARTICLE_INDEX, guide_section)
                stack = []
                break

        # Insert guidelines until the stack is empty.
        while len(stack) > 0:
            guideline = stack.pop(0)
            guideline_num = get_reg_number(guideline)
            inserted_index = recursive_insert(reg_section.content, guideline, guideline_num, stack)
            assert inserted_index != -1

    return ast_combined


def recursive_insert(root, guideline, guideline_num, stack) -> int:
    """
    Insert the guideline using a recursive algorithm.
    """
    inserted_index = -1  # We use this as a flag and as an auxiliary variable to insert.
    for index, node in enumerate(root):
        if inserted_index != -1:
            # The guideline was inserted in the previous iteration.
            break
        if hasattr(node, 'siblings') and node.siblings:
            # The 'siblings' boolean attribute is used to insert after the guideline with the most pluses (+).
            continue

        node_num = get_reg_number(node)

        # if len == len and node_num >= guideline_num.
        if len(node_num) == len(guideline_num) and not compare_reg_numbers(node_num, guideline_num):
            if node_num == guideline_num:
                # The guideline goes below the current node.
                inserted_index = index + 1
            elif compare_reg_numbers(guideline_num, node_num):
                # We have len == len, but the iteration went over the number without finding a regulation with the same
                # number. The guideline doesn't have an associated regulation, so we insert it before the current node.
                inserted_index = index

            # Insert:
            node.siblings = True
            root.insert(inserted_index, guideline)

            # Now we look if we have more guidelines for the same regulation in the stack, and we add all of them
            # together.
            while len(stack) > 0 and get_reg_number(stack[0]) == guideline_num:
                plus_guideline = stack.pop(0)
                root[inserted_index].siblings = True
                inserted_index += 1
                root.insert(inserted_index, plus_guideline)

            # Move the children of the affected Regulation to the children of the last Guideline added
            # for such Regulation.
            root[inserted_index].children = node.children
            node.children = []
            break

        # The first part of the numeration matches, but the numeration of the guideline is longer, so we go down
        # with the current node as the root.
        elif len(node_num) < len(guideline_num) and node_num == guideline_num[:len(node_num)]:
            inserted_index = recursive_insert(node.children, guideline, guideline_num, stack)

        # else: next node.

    if inserted_index == -1:
        # If we couldn't insert the guideline anywhere, we insert it at the end of the root's content.
        root.append(guideline)
        inserted_index = len(root) - 1

    return inserted_index
