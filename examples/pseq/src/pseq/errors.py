"""Erros com mensagem acionavel e codigo de saida estavel."""

EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2
EXIT_DATA = 3
EXIT_INTERRUPT = 130


class PseqError(Exception):
    """Erro esperado: sabe o que aconteceu, por que, e como corrigir."""

    def __init__(self, message: str, hint: str | None = None, code: int = EXIT_RUNTIME):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.code = code

    def render(self) -> str:
        lines = [f"Error: {self.message}"]
        if self.hint:
            lines.append(f"Try: {self.hint}")
        return "\n".join(lines)
