import pytest

from aegis.core.commands import (
    MAX_COMMAND_LENGTH,
    CommandError,
    InputSource,
    normalize_phrase,
    normalize_token,
    parse_command,
)


def test_parse_simple_command():
    req = parse_command("  Abrir   Bloco de Notas ")
    assert req.keyword == "abrir"
    assert req.args == ("Bloco", "de", "Notas")
    assert req.raw_text == "Abrir   Bloco de Notas"
    assert req.source is InputSource.TEXT


def test_keyword_normalization():
    assert parse_command("HORÁRIO?").keyword == "horario"
    assert normalize_token("Ação!") == "acao"
    assert normalize_phrase("  O Bloco,  de Notas ") == "o bloco de notas"


def test_wake_word_is_ignored():
    req = parse_command("AEGIS, hora", InputSource.VOICE)
    assert req.keyword == "hora"
    assert req.source is InputSource.VOICE


def test_wake_word_alone():
    with pytest.raises(CommandError, match="Estou aqui"):
        parse_command("Aegis")


@pytest.mark.parametrize("text", ["", "   ", "\n"])
def test_empty_rejected(text):
    with pytest.raises(CommandError):
        parse_command(text)


def test_too_long_rejected():
    with pytest.raises(CommandError, match="longo"):
        parse_command("a" * (MAX_COMMAND_LENGTH + 1))


@pytest.mark.parametrize("text", ["hora\x00", "ho\x1bra", "abrir\tbloco", "hora​"])
def test_control_characters_rejected(text):
    with pytest.raises(CommandError, match="controle"):
        parse_command(text)


def test_leading_bom_is_ignored():
    # PowerShell insere BOM ao redirecionar texto para o stdin.
    assert parse_command("﻿ajuda").keyword == "ajuda"
    with pytest.raises(CommandError, match="controle"):
        parse_command("aju﻿da")


def test_punctuation_only_keyword_rejected():
    with pytest.raises(CommandError):
        parse_command("!!! hora")


def test_non_string_rejected():
    with pytest.raises(CommandError):
        parse_command(None)  # type: ignore[arg-type]
