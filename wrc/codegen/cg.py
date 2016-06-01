from wrc.sema.ast import ASTVisitor

class CGDocument(ASTVisitor):
    def __init__(self):
        super(CGDocument, self).__init__()
        self.codegen = None
        # Accepted doctypes, set by subclass
        self.doctype = None

    def emit(self, ast):
        if not isinstance(ast, self.doctype):
            print "Can't generate code for this ast(" + str(type(ast)) + ")"
            print "Accepted type : " + str(self.doctype)
            return None
        if self.visit(ast):
            return self.codegen
        else:
            return None
