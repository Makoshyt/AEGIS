import pytest

from aegis.config import DEFAULT_CONFIG_FILE, ConfigError, load_config

from conftest import make_config


def test_default_file_loads(config, tmp_path):
    assert config.general.name == "AEGIS"
    assert config.hotkey.sequence == "Ctrl+Alt+A"
    assert config.voice.voice_name == "Maria"
    assert config.voice.enabled is False
    assert config.llm.enabled is False
    assert config.llm.model == "qwen2.5:7b"
    assert set(config.apps) == {"bloco", "calculadora"}
    assert config.log_dir == (tmp_path / "var" / "logs").resolve()
    assert DEFAULT_CONFIG_FILE in config.sources


def test_local_file_overrides_defaults(tmp_path):
    cfg = make_config(tmp_path, '[logging]\nlevel = "DEBUG"\n[ui]\nhistory_limit = 50\n')
    assert cfg.logging.level == "DEBUG"
    assert cfg.ui.history_limit == 50
    assert cfg.logging.file_name == "aegis.log"  # valor padrão preservado


def test_code_defaults_when_no_files(tmp_path):
    cfg = load_config(
        default_file=tmp_path / "x.toml", local_file=tmp_path / "y.toml", root=tmp_path
    )
    assert cfg.hotkey.sequence == "Ctrl+Alt+A"
    assert cfg.apps == {}
    assert cfg.sources == ()


def test_explicit_path_must_exist(tmp_path):
    with pytest.raises(ConfigError, match="não encontrado"):
        load_config(tmp_path / "nao_existe.toml", root=tmp_path)


@pytest.mark.parametrize(
    "toml, message",
    [
        ("[desconhecida]\nx = 1\n", "Seção"),
        ("[logging]\nnivel = 'INFO'\n", "desconhecida"),
        ("[logging]\nmax_bytes = true\n", "int"),
        ("[ui]\nstart_hidden = 'sim'\n", "bool"),
        ("[logging]\nlevel = 'VERBOSE'\n", "level"),
        ("[logging]\ndirectory = '../fora'\n", "fora"),
        ("[logging]\ndirectory = 'C:/Windows'\n", "relativo"),
        ("[logging]\nfile_name = '../x.log'\n", "file_name"),
        ("[ui]\nhistory_limit = 1\n", "history_limit"),
        ("[voice]\nenabled = true\n", "voz"),
        ("[llm]\nenabled = true\n", "LLM"),
        ("[llm]\nendpoint = 'https://api.exemplo.com'\n", "local"),
        ("[logging\n", "TOML inválido"),
    ],
)
def test_invalid_config_rejected(tmp_path, toml, message):
    with pytest.raises(ConfigError, match=message):
        make_config(tmp_path, toml)


@pytest.mark.parametrize(
    "path",
    [
        "notepad.exe",  # relativo
        r"C:\Windows\System32\cmd.exe /c dir",  # argumentos
        r'"C:\Windows\System32\cmd.exe"',  # aspas
        r"\\servidor\share\app.exe",  # rede
        r"C:\scripts\tarefa.bat",  # não é .exe
        r"C:\scripts\tarefa.ps1",
    ],
)
def test_invalid_app_paths_rejected(tmp_path, path):
    toml = f"[apps.teste]\nlabel = 'Teste'\npath = '{path}'\n"
    with pytest.raises(ConfigError):
        make_config(tmp_path, toml)


def test_app_requires_exact_keys(tmp_path):
    toml = "[apps.teste]\nlabel = 'T'\npath = 'C:/a.exe'\nargs = '-x'\n"
    with pytest.raises(ConfigError, match="exatamente"):
        make_config(tmp_path, toml)


def test_app_key_format(tmp_path):
    with pytest.raises(ConfigError):
        make_config(tmp_path, "[apps.'Meu App']\nlabel = 'T'\npath = 'C:/a.exe'\n")


def test_config_is_immutable(config):
    with pytest.raises(AttributeError):
        config.general.name = "outro"
    with pytest.raises(TypeError):
        config.apps["novo"] = None
