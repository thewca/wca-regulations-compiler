"""Generic interface for a Backend"""

from wrc.sema.ast import ASTVisitor


class GenerationOptions:
    merged: bool
    auto_remove_translation_subsection: bool

    def __init__(self, merged=False, auto_remove_translation_subsection=False):
        self.merged = merged
        self.auto_remove_translation_subsection = auto_remove_translation_subsection


class CGDocument(ASTVisitor):
    """
    Provide a generic class to derive from when implementing a backend.
    Default codegen is a unicode string
    """

    name = "undefined"

    def __init__(self, cg_type, generation_options: GenerationOptions):
        super().__init__()
        self.cg_type = cg_type
        self.codegen = self.cg_type()
        self.generation_options = generation_options

    def emit(self, ast_reg, ast_guide):
        """Default emit method: visit both ASTs and return the codegen"""
        if ast_reg:
            self.visit(ast_reg)
        codegen_reg = self.codegen
        self.codegen = self.cg_type()
        if ast_guide:
            self.visit(ast_guide)
        return (codegen_reg, self.codegen)

    def shouldEmitSubsection(self, language, title):
        return not (
            self.generation_options.auto_remove_translation_subsection
            and language == "english"
            and title == "Translation"
        )
