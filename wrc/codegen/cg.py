from wrc.sema.ast import ASTVisitor

class CGDocument(ASTVisitor):
    def __init__(self):
        super(CGDocument, self).__init__()
        self.codegen = None

    def emit(self, ast_reg, ast_guide):
        self.visit(ast_reg)
        self.visit(ast_guide)
        return self.codegen
