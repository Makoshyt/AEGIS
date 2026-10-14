"""Modo texto interativo, sem Qt. Usa o mesmo núcleo da janela."""

from __future__ import annotations

from collections.abc import Callable

from aegis.config import AegisConfig
from aegis.core.assistant import Assistant
from aegis.core.commands import normalize_token

EXIT_WORDS = frozenset({"sair", "exit", "quit"})


def run_cli(
    config: AegisConfig,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    assistant: Assistant | None = None,
) -> int:
    assistant = assistant or Assistant(config, mode="cli")
    output_fn(f"{config.general.name} (modo texto). Digite 'ajuda' ou 'sair'.")
    while True:
        try:
            line = input_fn(f"{config.general.name}> ")
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            break
        if not line.strip():
            continue
        if normalize_token(line.strip()) in EXIT_WORDS:
            break
        output_fn(assistant.submit(line).message)
    output_fn("Até logo.")
    return 0
