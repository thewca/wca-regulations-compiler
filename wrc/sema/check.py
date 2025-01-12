""" This module implements several semantic analysis on the Regulations and Guidelines """
import re

from wrc.sema.ast import ASTVisitor, WCAGuidelines, WCARegulations

class SemaAnalysis(ASTVisitor):
    """ Basic class for a pass """
    def __init__(self):
        super(SemaAnalysis, self).__init__()
        self.errors = []
        self.warnings = []

class HierarchyCheck(SemaAnalysis):
    """
    Hierarchy checker: check that every regulation is correctly
    nested in its correct parent, and comes after the previous regulation.
    """
    def __init__(self):
        super(HierarchyCheck, self).__init__()
        self.lastrule = [None]
        self.err_misplaced = "%s %s misplaced in section %s"
        self.err_precedence = "%s %s comes after %s when it shouldn't"
        self.err_reg_in_guide = "Expected a Guideline, got Regulation %s"
        self.err_guide_in_reg = "Expected a Regulation, got Guideline %s"

    def visitArticle(self, article):
        self.lastrule = [None]
        return super(HierarchyCheck, self).visitArticle(article)

    def visitRegulation(self, rule):
        retval = self.visitRule(rule)
        self.lastrule.append(None)
        retval = retval and self.visit(rule.children)
        self.lastrule.pop()
        return retval

    def visitGuideline(self, rule):
        return self.visitRule(rule)

    def visitRule(self, reg):
        last = self.lastrule[-1]
        # Here parent cannot be none, it's either another regulation or an article
        # (both have a "number" member)
        if (not reg.number.startswith(reg.parent.number) or
                (self.rootnode_type == WCARegulations and
                 reg.parent.depth() + 1 != reg.depth())):
            self.errors.append(self.err_misplaced %
                               (str(reg.__class__.__name__),
                                reg.number,
                                reg.parent.number))
        elif last and reg <= last:
            self.errors.append(self.err_precedence %
                               (str(reg.__class__.__name__),
                                reg.number,
                                last.number))
        if self.rootnode_type == WCAGuidelines and reg.number.count('+') == 0:
            self.errors.append(self.err_reg_in_guide % (reg.number))

        if self.rootnode_type == WCARegulations and reg.number.count('+') != 0:
            self.errors.append(self.err_guide_in_reg % (reg.number))

        self.lastrule[-1] = reg
        return True

class LabelCheck(SemaAnalysis):
    """
    Check that every label used in the guidelines is actually defined
    at the beginning of the document
    """
    def __init__(self):
        super(LabelCheck, self).__init__()
        self.labels = dict()
        self.err_duplicate = "Duplicate label %s"
        self.err_undefined = "Guideline %s uses label %s which is undefined"
        self.warn_unused = "Unused label %s"

    def visitLabelDecl(self, label):
        if label in self.labels:
            self.errors.append(self.err_duplicate % label.name)
        else:
            self.labels[label] = False
        return True

    def visitGuideline(self, reg):
        if reg.labelname in self.labels:
            self.labels[reg.labelname] = True
        else:
            self.errors.append(self.err_undefined % (reg.number, reg.labelname))
        return True

    def end_of_document(self, document):
        for key, value in self.labels.items():
            if not value:
                self.warnings.append(self.warn_unused % key.name)
        return True


class ReferenceCheck(SemaAnalysis):
    """
    Reference checker (Singleton):
    * Avoid rules referencing other non-existent/removed rules.
    * Avoid invalid references (e.g. 'regulations:guideline:...', 'guidelines:regulation:...' or 'REgulations:...:...').

    A "node" may be either an article or a rule.
    A "rule" may be either a regulation or a guideline (they are handled the same way).
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        else:
            # The parser (client of this class) accumulates the errors after visiting an entire WCADocument.
            # Here we are keeping state, so we want to avoid duplicated errors and warnings.
            cls._instance.errors.clear()
            cls._instance.warnings.clear()

        return cls._instance


    def __init__(self):
        super(ReferenceCheck, self).__init__()
        self.visited_regulations = False
        self.visited_guidelines = False

        # Example: self.rules_references = {
        #   "1a": {"found": bool, "referenced_by": list[str]},
        # }
        self.rules_references = {}
        self.articles_references = {}

        self.reference_regex = re.compile(r"\[[^\n\r\[\]]*]\((\w+:(\w+):(\w+\+*))\)", re.IGNORECASE)
        # Examples of valid sections:
        # 'regulations:regulation:1a'
        # 'guidelines:guideline:5b5f+'
        # 'regulations:article:12'
        # We are not too strict on the format of the article/rule number here.
        self.valid_sections_regex = re.compile(
            r"regulations:regulation:[A-Za-z0-9]+|guidelines:guideline:[A-Za-z0-9]+\++|regulations:article:(?:[A-Z]+|[0-9]+)"
        )

        # Logger errors.
        self.err_missing_referenced = "%s %s is referenced in %s, but was not found"
        self.err_invalid_reference = "%s has an invalid reference: '%s'"

    def visit(self, o):
        if isinstance(o, WCARegulations):
            self.visited_regulations = True
        elif isinstance(o, WCAGuidelines):
            self.visited_guidelines = True
        return super(ReferenceCheck, self).visit(o)

    def visitArticle(self, article):
        self._mark_node_as_found(article.number, self.articles_references)
        return super(ReferenceCheck, self).visitArticle(article)

    def visitRegulation(self, reg):
        return self.visitRule(reg) and super(ReferenceCheck, self).visit(reg.children)

    def visitGuideline(self, reg):
        return self.visitRule(reg) and super(ReferenceCheck, self).visit(reg.children)

    def visitRule(self, visited_rule):

        self._mark_node_as_found(visited_rule.number, self.rules_references)

        # Check references to other rules.
        # We first match Markdown links that look like '[...](...:...:...)'.
        # The part within round brackets is the reference.
        for match in self.reference_regex.finditer(visited_rule.text):
            full_reference = match.group(1)

            # Check if the sections of the reference are valid.
            if not self.valid_sections_regex.fullmatch(full_reference):
                self.errors.append(self.err_invalid_reference % (visited_rule.number, full_reference))
                continue

            node_type = match.group(2).lower()  # (article|regulation|guideline)
            referenced_node_number = match.group(3)

            self._add_reference_to_dictionary(referenced_node_number, visited_rule.number, node_type)

        return True

    def end_of_document(self, document):
        if self.visited_regulations and self.visited_guidelines:
            # Find references to missing nodes.
            self._append_errors_from_dictionary("Rule", self.rules_references)
            self._append_errors_from_dictionary("Article", self.articles_references)

        return True

    def _append_errors_from_dictionary(self, node_type: str, dictionary: dict) -> None:
        for node_number, node_data in dictionary.items():
            if not node_data["found"]:
                self.errors.append(
                    self.err_missing_referenced % (node_type, node_number, node_data["referenced_by"])
                )

    def _add_reference_to_dictionary(self, referenced_node_number: str, referencing_node_number: str, node_type: str) -> None:
        if node_type == "article":
            dictionary = self.articles_references
        else:
            dictionary = self.rules_references

        if referenced_node_number in dictionary:
            dictionary[referenced_node_number]["referenced_by"].append(referencing_node_number)
        else:
            dictionary[referenced_node_number] = {
                "found": False,
                "referenced_by": [referencing_node_number]
            }

    @staticmethod
    def _mark_node_as_found(node_number: str, dictionary: dict) -> None:
        if node_number in dictionary:
            dictionary[node_number]["found"] = True
        else:
            dictionary[node_number] = {
                "found": True,
                "referenced_by": []
            }
