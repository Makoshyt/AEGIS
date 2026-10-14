"""Configuração centralizada do AEGIS.

Ordem de precedência (a última vence):

1. Valores padrão definidos nas dataclasses abaixo.
2. ``config/aegis.default.toml`` (versionado).
3. ``config/aegis.local.toml`` (opcional, ignorado pelo Git) ou o arquivo passado em ``--config``.

Chaves desconhecidas, tipos incorretos e valores fora dos limites geram ``ConfigError``.
"""

from __future__ import annotations

import re
import tomllib
import typing
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path, PureWindowsPath
from types import MappingProxyType
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "config" / "aegis.default.toml"
LOCAL_CONFIG_FILE = PROJECT_ROOT / "config" / "aegis.local.toml"

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
MAX_ALLOWED_APPS = 50
_APP_KEY_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
_FILE_NAME_RE = re.compile(r"^[\w.-]{1,64}$")
_LOCAL_ENDPOINTS = ("http://127.0.0.1", "http://localhost")


class ConfigError(ValueError):
    """Configuração ausente, malformada ou inválida."""


@dataclass(frozen=True)
class GeneralConfig:
    name: str = "AEGIS"
    language: str = "pt-BR"


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    directory: str = "var/logs"
    file_name: str = "aegis.log"
    max_bytes: int = 1_000_000
    backup_count: int = 5
    log_command_text: bool = False


@dataclass(frozen=True)
class UIConfig:
    start_hidden: bool = False
    close_to_tray: bool = True
    history_limit: int = 500


@dataclass(frozen=True)
class HotkeyConfig:
    enabled: bool = True
    sequence: str = "Ctrl+Alt+A"


@dataclass(frozen=True)
class VoiceConfig:
    enabled: bool = False
    voice_name: str = "Maria"
    language: str = "pt-BR"


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool = False
    provider: str = "ollama"
    model: str = "qwen2.5:7b"
    endpoint: str = "http://127.0.0.1:11434"


@dataclass(frozen=True)
class AllowedApp:
    key: str
    label: str
    path: str


@dataclass(frozen=True)
class AegisConfig:
    root: Path
    general: GeneralConfig = field(default_factory=GeneralConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    apps: Mapping[str, AllowedApp] = field(default_factory=lambda: MappingProxyType({}))
    sources: tuple[Path, ...] = ()

    @property
    def var_dir(self) -> Path:
        return self.root / "var"

    @property
    def log_dir(self) -> Path:
        return (self.root / self.logging.directory).resolve()

    @property
    def log_file(self) -> Path:
        return self.log_dir / self.logging.file_name


_SECTIONS: dict[str, type] = {
    "general": GeneralConfig,
    "logging": LoggingConfig,
    "ui": UIConfig,
    "hotkey": HotkeyConfig,
    "voice": VoiceConfig,
    "llm": LLMConfig,
}


def load_config(
    path: str | Path | None = None,
    *,
    default_file: Path = DEFAULT_CONFIG_FILE,
    local_file: Path = LOCAL_CONFIG_FILE,
    root: Path = PROJECT_ROOT,
) -> AegisConfig:
    """Carrega, mescla e valida a configuração."""
    data: dict[str, Any] = {}
    sources: list[Path] = []

    if default_file.is_file():
        data = _merge(data, _read_toml(default_file))
        sources.append(default_file)

    override = Path(path) if path is not None else local_file
    if path is not None and not override.is_file():
        raise ConfigError(f"Arquivo de configuração não encontrado: {override}")
    if override.is_file():
        data = _merge(data, _read_toml(override))
        sources.append(override)

    return _build_config(data, Path(root).resolve(), tuple(sources))


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"TOML inválido em {path.name}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Não foi possível ler {path}: {exc}") from exc


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _build_config(data: dict[str, Any], root: Path, sources: tuple[Path, ...]) -> AegisConfig:
    unknown = set(data) - set(_SECTIONS) - {"apps"}
    if unknown:
        raise ConfigError(f"Seção(ões) desconhecida(s): {', '.join(sorted(unknown))}.")

    sections = {
        name: _build_section(cls, data.get(name, {}), name) for name, cls in _SECTIONS.items()
    }
    apps = _build_apps(data.get("apps", {}))
    config = AegisConfig(root=root, apps=apps, sources=sources, **sections)
    _validate(config)
    return config


def _build_section(cls: type, raw: Any, section: str) -> Any:
    if not isinstance(raw, dict):
        raise ConfigError(f"[{section}] deve ser uma tabela.")
    hints = typing.get_type_hints(cls)
    known = {f.name for f in fields(cls)}
    unknown = set(raw) - known
    if unknown:
        raise ConfigError(f"Chave(s) desconhecida(s) em [{section}]: {', '.join(sorted(unknown))}.")
    for name, value in raw.items():
        if not _is_instance(value, hints[name]):
            raise ConfigError(f"[{section}].{name} deve ser do tipo {hints[name].__name__}.")
    return cls(**raw)


def _is_instance(value: Any, expected: type) -> bool:
    # bool é subclasse de int; aqui os dois tipos são tratados de forma estrita.
    if expected is bool:
        return isinstance(value, bool)
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, expected)


def _build_apps(raw: Any) -> Mapping[str, AllowedApp]:
    if not isinstance(raw, dict):
        raise ConfigError("[apps] deve ser uma tabela.")
    if len(raw) > MAX_ALLOWED_APPS:
        raise ConfigError(f"[apps] aceita no máximo {MAX_ALLOWED_APPS} aplicativos.")
    apps: dict[str, AllowedApp] = {}
    for key, entry in raw.items():
        if not _APP_KEY_RE.match(key):
            raise ConfigError(f"[apps.{key}]: use apenas letras minúsculas, dígitos, '-' ou '_'.")
        if not isinstance(entry, dict) or set(entry) != {"label", "path"}:
            raise ConfigError(f"[apps.{key}] deve conter exatamente as chaves 'label' e 'path'.")
        label, path = entry["label"], entry["path"]
        if not isinstance(label, str) or not 0 < len(label.strip()) <= 60:
            raise ConfigError(f"[apps.{key}].label deve ter entre 1 e 60 caracteres.")
        if not isinstance(path, str):
            raise ConfigError(f"[apps.{key}].path deve ser texto.")
        _validate_exe_path(key, path)
        apps[key] = AllowedApp(key=key, label=label.strip(), path=path)
    return MappingProxyType(apps)


def _validate_exe_path(key: str, path: str) -> None:
    if not path or '"' in path or "\x00" in path:
        raise ConfigError(f"[apps.{key}].path contém caracteres inválidos.")
    if path.startswith(("\\\\", "//")):
        raise ConfigError(f"[apps.{key}].path não pode apontar para um caminho de rede.")
    win_path = PureWindowsPath(path)
    if not win_path.is_absolute():
        raise ConfigError(f"[apps.{key}].path deve ser um caminho absoluto.")
    if win_path.suffix.lower() != ".exe":
        raise ConfigError(f"[apps.{key}].path deve apontar para um arquivo .exe, sem argumentos.")
    if any(part != part.strip() for part in win_path.parts[1:]):
        raise ConfigError(f"[apps.{key}].path contém espaços inválidos nas extremidades.")


def _validate(config: AegisConfig) -> None:
    log = config.logging
    if log.level.upper() not in LOG_LEVELS:
        raise ConfigError(f"[logging].level deve ser um de: {', '.join(LOG_LEVELS)}.")
    if not 10_000 <= log.max_bytes <= 100_000_000:
        raise ConfigError("[logging].max_bytes deve estar entre 10000 e 100000000.")
    if not 0 <= log.backup_count <= 50:
        raise ConfigError("[logging].backup_count deve estar entre 0 e 50.")
    if not _FILE_NAME_RE.match(log.file_name):
        raise ConfigError("[logging].file_name deve ser um nome de arquivo simples.")
    if Path(log.directory).is_absolute() or PureWindowsPath(log.directory).is_absolute():
        raise ConfigError("[logging].directory deve ser relativo à pasta do projeto.")
    if not config.log_dir.is_relative_to(config.root):
        raise ConfigError("[logging].directory não pode apontar para fora da pasta do projeto.")

    if not 10 <= config.ui.history_limit <= 10_000:
        raise ConfigError("[ui].history_limit deve estar entre 10 e 10000.")
    if not config.hotkey.sequence.strip():
        raise ConfigError("[hotkey].sequence não pode ser vazio.")

    if config.voice.enabled:
        raise ConfigError("[voice].enabled: voz ainda não está disponível nesta fase.")
    if config.llm.enabled:
        raise ConfigError("[llm].enabled: integração com LLM ainda não está disponível nesta fase.")
    if not config.llm.endpoint.startswith(_LOCAL_ENDPOINTS):
        raise ConfigError("[llm].endpoint deve ser local (127.0.0.1 ou localhost).")
