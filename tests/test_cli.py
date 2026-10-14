from aegis.cli import run_cli
from aegis.core.assistant import Assistant

from conftest import FIXED_NOW


def test_cli_session(config):
    inputs = iter(["hora", "", "comando-desconhecido", "sair", "nunca lido"])
    output = []
    assistant = Assistant(config, mode="cli", clock=lambda: FIXED_NOW, launcher=lambda p: None)
    code = run_cli(
        config, input_fn=lambda _: next(inputs), output_fn=output.append, assistant=assistant
    )
    assert code == 0
    assert "09:05 — segunda-feira, 1 de janeiro de 2024." in output
    assert any("Não conheço" in line for line in output)
    assert output[-1] == "Até logo."


def test_cli_handles_eof(config):
    def raise_eof(_):
        raise EOFError

    assert run_cli(config, input_fn=raise_eof, output_fn=lambda _: None) == 0


def test_main_rejects_invalid_config(tmp_path, capsys):
    from aegis.__main__ import EXIT_CONFIG_ERROR, main

    bad = tmp_path / "ruim.toml"
    bad.write_text("[voice]\nenabled = true\n", encoding="utf-8")
    assert main(["--cli", "--config", str(bad)]) == EXIT_CONFIG_ERROR
    assert "Erro de configuração" in capsys.readouterr().err
