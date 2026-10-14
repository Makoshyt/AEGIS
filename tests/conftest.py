import os

# Testes de interface rodam sem exibir janelas.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from aegis.config import DEFAULT_CONFIG_FILE, AegisConfig, load_config  # noqa: E402
from aegis.logging_setup import shutdown_logging  # noqa: E402

FIXED_NOW = datetime(2024, 1, 1, 9, 5, 0)  # segunda-feira


def make_config(tmp_path: Path, local_toml: str = "") -> AegisConfig:
    """Configuração real padrão + sobrescritas, com a raiz do projeto em ``tmp_path``."""
    local = tmp_path / "local.toml"
    local.write_text(local_toml, encoding="utf-8")
    return load_config(default_file=DEFAULT_CONFIG_FILE, local_file=local, root=tmp_path)


@pytest.fixture
def config(tmp_path: Path) -> AegisConfig:
    return make_config(tmp_path)


@pytest.fixture(autouse=True)
def _close_logging():
    yield
    shutdown_logging()
