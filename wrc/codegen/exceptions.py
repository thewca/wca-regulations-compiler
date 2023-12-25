
class CombinerBadFormat(Exception):
    def __init__(self, error):
        self.message = f"Internal error: {error}. Please report this issue."
        super().__init__(self.message)


class CombinerNotFound(Exception):
    def __init__(self, msg):
        self.message = f"{msg} not found."
        super().__init__(self.message)
