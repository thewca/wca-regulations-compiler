"""This module implements several semantic analysis on the Regulations and Guidelines"""

from wrc.sema.ast import ASTVisitor


class SemaAnalysis(ASTVisitor):
    """Basic class for a pass"""

    def __init__(self):
        super().__init__()
        self.errors = []
        self.warnings = []


class HierarchyCheck(SemaAnalysis):
    """
    Hierarchy checker: check that every regulation is correctly
    nested in its correct parent, and comes after the previous regulation.
    """

    def __init__(self):
        super().__init__()
        self.lastrule = [None]
        self.err_misplaced = "%s %s misplaced in section %s"
        self.err_precedence = "%s %s comes after %s when it shouldn't"
        self.err_reg_in_guide = "Expected a Guideline, got Regulation %s"
        self.err_guide_in_reg = "Expected a Regulation, got Guideline %s"

    def visitArticle(self, article):
        self.lastrule = [None]
        return super().visitArticle(article)

    def visitRegulation(self, reg):
        retval = self.visitRule(reg)
        self.lastrule.append(None)
        retval = retval and self.visit(reg.children)
        self.lastrule.pop()
        return retval

    def visitGuideline(self, reg):
        return self.visitRule(reg)

    def visitRule(self, rule):
        last = self.lastrule[-1]
        # Here parent cannot be none, it's either another regulation or an article
        # (both have a "number" member)
        if not rule.number.startswith(rule.parent.number):
            self.errors.append(
                self.err_misplaced
                % (str(rule.__class__.__name__), rule.number, rule.parent.number)
            )
        elif last and rule <= last:
            self.errors.append(
                self.err_precedence
                % (str(rule.__class__.__name__), rule.number, last.number)
            )

        self.lastrule[-1] = rule
        return True


class LabelCheck(SemaAnalysis):
    """
    Check that every label used in the guidelines is actually defined
    at the beginning of the document
    """

    def __init__(self):
        super().__init__()
        self.labels = {}
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
