import logging

import pytest

from aegis.core.assistant import Assistant
from aegis.logging_setup import REDACTED, redact, setup_logging, shutdown_logging

from conftest import make_config


@pytest.mark.parametrize(
    "text, secret",
    [
        ("senha=minhaSenha123", "minhaSenha123"),
        ("password: 'p@ss w0rd'", "p@ss w0rd"),
        ("Authorization: Bearer abc.def.ghi123", "abc.def.ghi123"),
        ("GET /api?token=XYZ987&page=2", "XYZ987"),
        ("api_key = sk-proj-1234567890abcdefghij", "sk-proj-1234567890abcdefghij"),
        ("usando chave ghp_abcdefghijklmnopqrstuvwxyz123456", "ghp_abcdefghijklmnopqrstuvwxyz123456"),
        ("aws AKIAABCDEFGHIJKLMNOP ok", "AKIAABCDEFGHIJKLMNOP"),
        ("contato: fulano.silva@exemplo.com.br", "fulano.silva@exemplo.com.br"),
        (r"arquivo C:\Users\marco\Documents\x.txt", "marco"),
        ("arquivo C:/Users/marco/x.txt", "marco"),
    ],
)
def test_redact_masks_sensitive_values(text, secret):
    result = redact(text)
    assert secret not in result


def test_redact_keeps_normal_text():
    text = "habilidade=hora origem=texto ok=True duracao_ms=0.3"
    assert redact(text) == text
    assert redact("o token de acesso expirou") == "o token de acesso expirou"


def test_redact_preserves_key_name():
    assert redact("senha=abc") == f"senha={REDACTED}"
    assert redact(r"C:\Users\marco\x") == r"C:\Users\<usuario>\x"


def _read_log(config) -> str:
    shutdown_logging()  # fecha e descarrega os handlers
    return config.log_file.read_text(encoding="utf-8")


def test_log_file_is_redacted(config):
    log_file = setup_logging(config, console_level=None)
    assert log_file.is_relative_to(config.root)
    logging.getLogger("aegis.teste").warning("login senha=segredo42 email a@b.com")
    content = _read_log(config)
    assert "segredo42" not in content
    assert "a@b.com" not in content
    assert "senha=[REDACTED]" in content


def test_traceback_is_redacted(config):
    setup_logging(config, console_level=None)
    try:
        raise RuntimeError("falha com token=ABCDEF123456")
    except RuntimeError:
        logging.getLogger("aegis.teste").exception("erro")
    content = _read_log(config)
    assert "Traceback" in content
    assert "ABCDEF123456" not in content


def test_setup_logging_is_idempotent(config):
    setup_logging(config, console_level=None)
    setup_logging(config, console_level=None)
    assert len(logging.getLogger("aegis").handlers) == 1


def test_command_text_not_logged_by_default(config):
    setup_logging(config, console_level=None)
    assistant = Assistant(config, mode="teste")
    assistant.submit("ajuda marcadorunico")
    assistant.submit("comandoinexistente marcadorunico")
    content = _read_log(config)
    assert "marcadorunico" not in content
    assert "comandoinexistente" not in content
    assert "habilidade=ajuda" in content


def test_command_text_logged_when_enabled_but_redacted(tmp_path):
    config = make_config(tmp_path, "[logging]\nlog_command_text = true\n")
    setup_logging(config, console_level=None)
    Assistant(config, mode="teste").submit("ajuda marcadorunico senha=xyz789")
    content = _read_log(config)
    assert "marcadorunico" in content
    assert "xyz789" not in content
