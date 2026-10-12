"""Text input utilities for interactive paste and local file ingestion."""

import sys
from pathlib import Path
from typing import Optional


def read_from_clipboard_or_input(prompt_message: Optional[str] = None) -> str:
    """
    Interactively read multiline job text from user terminal input.
    Accepts input until EOF (Ctrl+D on Linux/macOS, Ctrl+Z on Windows)
    or typing 'EOF' or '---END---' on an empty line.
    """
    if prompt_message:
        print(prompt_message)
    else:
        print("=" * 70)
        print("PEGA EL TEXTO DE LA OFERTA DE EMPLEO A CONTINUACIÓN:")
        print("(Al terminar, pulsa Ctrl+D en Linux o escribe 'EOF' en una línea nueva)")
        print("=" * 70)

    lines = []
    try:
        while True:
            line = sys.stdin.readline()
            if not line:  # EOF reached
                break
            stripped = line.strip()
            if stripped in ("EOF", "---END---", ":q"):
                break
            lines.append(line)
    except KeyboardInterrupt:
        print("\nLectura cancelada por el usuario.")
        sys.exit(0)

    text = "".join(lines).strip()
    if not text:
        raise ValueError("El texto introducido está vacío.")
    return text


def read_from_file(file_path: str) -> str:
    """Read job description text from a local file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"El archivo especificado no existe: {file_path}")
    if not path.is_file():
        raise ValueError(f"La ruta no corresponde a un archivo regular: {file_path}")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"El archivo {file_path} está vacío.")
    return content
