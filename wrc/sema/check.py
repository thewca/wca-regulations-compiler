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
    Reference checker:
    * Avoid rules referencing other non-existent/removed rules.
    * Avoid invalid references (e.g. 'regulations:guideline:...', 'guidelines:regulation:...' or 'REgulations:...:...').

    A "node" may be either an article or a rule.
    A "rule" may be either a regulation or a guideline (they are handled the same way).
    """
    def __init__(self):
        super(ReferenceCheck, self).__init__()
        self.rules_references = {}
        self.articles_references = {}
        # Example: self.rules_references = {
        #   "1a": {"found": bool, "referenced_by": list[str]},
        #   ...
        # }
        # The same applies to self.articles_references.
        self.node_reference_regex = re.compile(r"(regulations|guidelines):(article|regulation|guideline):([a-z0-9]+\+*)",
                                               re.IGNORECASE)
        self.err_missing_referenced_rule = "Rule %s is referenced in %s, but was not found"
        self.err_missing_referenced_article = "Article %s is referenced in %s, but was not found"
        self.err_invalid_reference = "%s has an invalid reference: '%s'"
        self.err_uppercase_section = "got reference '%s' in %s, but '%s' must be all lowercase"

    def visitArticle(self, article):

        # Mark article as found.
        if article.number in self.articles_references:
            self.articles_references[article.number].found = True
        else:
            self.articles_references[article.number] = {
                "found": True,
                "referenced_by": []
            }

        return True

    def visitRule(self, visited_rule):

        # Check references to other rules.
        for match in self.node_reference_regex.finditer(visited_rule.text):
            full_reference = match.group(0)
            document_type = match.group(1)  # (regulations|guidelines)
            node_type = match.group(2)      # (article|regulation|guideline)
            referenced_node_number = match.group(3)
            document_type_lower = document_type.lower()
            node_type_lower = node_type.lower()

            # Check uppercase sections (the first two parts of a reference).
            if document_type != document_type_lower:
                self.errors.append(self.err_uppercase_section % (full_reference, visited_rule.number, document_type))
            if node_type != node_type_lower:
                self.errors.append(self.err_uppercase_section % (full_reference, visited_rule.number, node_type))

            # Check invalid reference sections.
            if (document_type_lower == "regulations" and node_type_lower == "guideline") or (
                    document_type_lower == "guidelines" and node_type_lower == "regulation"):
                self.errors.append(self.err_invalid_reference % (visited_rule.number, full_reference))

            # Handle reference dictionary.
            if node_type_lower == "article":
                dictionary = self.articles_references
            else:
                dictionary = self.rules_references

            if referenced_node_number in dictionary:
                dictionary[referenced_node_number].referenced_by.append(visited_rule.number)
            else:
                dictionary[referenced_node_number] = {
                    "found": False,
                    "referenced_by": [visited_rule.number]
                }

        # Mark the current rule as found.
        if visited_rule.number in self.rules_references:
            self.rules_references[visited_rule.number].found = True
        else:
            self.rules_references[visited_rule.number] = {
                "found": True,
                "referenced_by": []
            }

        return True

    def end_of_document(self, document):
        # Check if a referenced node was not found.
        for rule_number, rule_data in self.rules_references.items():
            if not rule_data.found:
                self.errors.append(self.err_missing_referenced_rule % (rule_number, rule_data.referenced_by))

        for article_number, article_data in self.articles_references.items():
            if not article_data.found:
                self.errors.append(self.err_missing_referenced_article % (article_number, article_data.referenced_by))

        return True
