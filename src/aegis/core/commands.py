"""Conversão de texto em ``CommandRequest``.

A análise é puramente léxica: a primeira palavra identifica a habilidade e o restante vira
argumentos. O texto nunca é interpretado, avaliado ou repassado a um shell.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum

MAX_COMMAND_LENGTH = 500
WAKE_WORDS = frozenset({"aegis"})
_EDGE_PUNCTUATION = ",.;:!?¡¿\"'()"


class InputSource(StrEnum):
    TEXT = "texto"
    VOICE = "voz"


class CommandError(ValueError):
    """Entrada que não pode ser transformada em comando; a mensagem é exibível ao usuário."""


@dataclass(frozen=True)
class CommandRequest:
    keyword: str
    args: tuple[str, ...]
    raw_text: str
    source: InputSource = InputSource.TEXT


def normalize_token(token: str) -> str:
    """Minúsculas, sem acentos e sem pontuação nas extremidades: 'Horário!' -> 'horario'."""
    decomposed = unicodedata.normalize("NFKD", token.casefold())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.strip(_EDGE_PUNCTUATION)


def normalize_phrase(text: str) -> str:
    return " ".join(t for t in (normalize_token(p) for p in text.split()) if t)


def parse_command(text: str, source: InputSource = InputSource.TEXT) -> CommandRequest:
    if not isinstance(text, str):
        raise CommandError("Comando inválido.")
    # Entrada redirecionada pelo PowerShell pode começar com BOM (U+FEFF).
    text = text.lstrip("﻿").strip()
    if not text:
        raise CommandError("Digite um comando. Use 'ajuda' para ver as opções.")
    if len(text) > MAX_COMMAND_LENGTH:
        raise CommandError(f"Comando muito longo (máximo de {MAX_COMMAND_LENGTH} caracteres).")
    if any(unicodedata.category(c) in ("Cc", "Cf") for c in text):
        raise CommandError("O comando contém caracteres de controle não permitidos.")

    tokens = text.split()
    if normalize_token(tokens[0]) in WAKE_WORDS:
        tokens = tokens[1:]
        if not tokens:
            raise CommandError("Estou aqui. Diga um comando, por exemplo: ajuda.")

    keyword = normalize_token(tokens[0])
    if not keyword:
        raise CommandError("Não entendi o comando. Use 'ajuda' para ver as opções.")
    return CommandRequest(keyword=keyword, args=tuple(tokens[1:]), raw_text=text, source=source)
