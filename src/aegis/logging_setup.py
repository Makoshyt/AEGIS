"""Configuração de logging com mascaramento de informações sensíveis.

O mascaramento é aplicado ao texto final formatado, incluindo tracebacks, para que
nenhum handler grave segredos, e-mails ou o nome do usuário do Windows.
"""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aegis.config import AegisConfig

LOGGER_NAME = "aegis"
REDACTED = "[REDACTED]"
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

_SECRET_KEYS = (
    r"authorization|password|passwd|pwd|senha|secret|segredo|token|"
    r"api[_-]?key|access[_-]?key|chave"
)

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # chave=valor / chave: valor (inclui "Authorization: Bearer xyz" e query strings).
    (
        re.compile(
            rf"(?i)\b({_SECRET_KEYS})\b(\s*[:=]\s*)(?:(?:bearer|basic)\s+)?"
            r"(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
        ),
        rf"\1\2{REDACTED}",
    ),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}"), rf"\1 {REDACTED}"),
    # Formatos conhecidos de tokens (OpenAI/Stripe, GitHub, AWS, JWT).
    (
        re.compile(
            r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"
            r"|\bgh[pousr]_[A-Za-z0-9]{20,}"
            r"|\bAKIA[0-9A-Z]{16}\b"
            r"|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
        ),
        REDACTED,
    ),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"(?i)\b([A-Z]:[\\/]+Users[\\/]+)[^\\/\s\"']+"), r"\1<usuario>"),
)


def redact(text: str) -> str:
    """Mascara segredos, e-mails e nomes de usuário em caminhos do Windows."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup_logging(config: AegisConfig, *, console_level: int | None = logging.INFO) -> Path:
    """Configura o logger ``aegis``. Pode ser chamada novamente sem duplicar handlers.

    ``console_level=None`` desativa a saída no console.
    """
    shutdown_logging()

    log_file = config.log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = RedactingFormatter(_FORMAT)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(config.logging.level.upper())
    logger.propagate = False

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.logging.max_bytes,
        backupCount=config.logging.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Em pythonw.exe não há console (sys.stderr é None).
    if console_level is not None and sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(console_level)
        console.setFormatter(formatter)
        logger.addHandler(console)

    return log_file


def shutdown_logging() -> None:
    """Fecha e remove os handlers do logger ``aegis``."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
