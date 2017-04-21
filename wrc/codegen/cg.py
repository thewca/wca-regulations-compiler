''' Generic interface for a Backend '''
from wrc.sema.ast import ASTVisitor

class CGDocument(ASTVisitor):
    '''
    Provide a generic class to derive from when implementing a backend.
    Default codegen is a unicode string
    '''
    name = "undefined"
    def __init__(self, cg_type):
        super(CGDocument, self).__init__()
        self.cg_type = cg_type
        self.codegen = self.cg_type()

    def emit(self, ast_reg, ast_guide):
        ''' Default emit method: visit both ASTs and return the codegen '''
        if (ast_reg):
            self.visit(ast_reg)
        codegen_reg = self.codegen
        self.codegen = self.cg_type()
        if (ast_guide):
            self.visit(ast_guide)
        return (codegen_reg, self.codegen)
