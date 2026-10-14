"""Ponto de entrada: ``python -m aegis [--cli] [--config ARQUIVO]``."""

from __future__ import annotations

import argparse
import logging
import platform
import sys
from types import TracebackType

from aegis import __version__
from aegis.config import ConfigError, load_config
from aegis.logging_setup import LOGGER_NAME, setup_logging, shutdown_logging

EXIT_CONFIG_ERROR = 2
EXIT_WRONG_PYTHON = 3


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="aegis", description="AEGIS IA, assistente pessoal.")
    parser.add_argument("--cli", action="store_true", help="modo texto no terminal, sem janela")
    parser.add_argument("--config", metavar="ARQUIVO", help="arquivo TOML que substitui o local")
    parser.add_argument("--version", action="version", version=f"AEGIS {__version__}")
    return parser.parse_args(argv)


def _error(message: str) -> None:
    if sys.stderr is not None:
        print(message, file=sys.stderr)


def _install_excepthook(log: logging.Logger) -> None:
    def hook(
        exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.critical("exceção não tratada", exc_info=(exc_type, exc, tb))

    sys.excepthook = hook


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if sys.version_info[:2] != (3, 12):
        _error(f"O AEGIS requer Python 3.12 (em uso: {platform.python_version()}).")
        return EXIT_WRONG_PYTHON

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        _error(f"Erro de configuração: {exc}")
        return EXIT_CONFIG_ERROR

    setup_logging(config, console_level=logging.WARNING if args.cli else logging.INFO)
    log = logging.getLogger(LOGGER_NAME)
    _install_excepthook(log)
    mode = "cli" if args.cli else "janela"
    log.info("AEGIS %s iniciando (Python %s, modo=%s)", __version__, platform.python_version(), mode)

    try:
        if args.cli:
            from aegis.cli import run_cli

            return run_cli(config)

        # Importado aqui para que o modo texto não dependa do Qt.
        from aegis.app import AegisApp

        return AegisApp(config).run()
    finally:
        log.info("AEGIS encerrado")
        shutdown_logging()


if __name__ == "__main__":
    sys.exit(main())
