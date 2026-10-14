from __future__ import annotations

import platform
import time
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from aegis import __version__
from aegis.config import AegisConfig
from aegis.skills.base import Skill, SkillResult

if TYPE_CHECKING:
    from aegis.skills.registry import SkillRegistry


def format_uptime(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}min"
    if minutes:
        return f"{minutes}min {secs:02d}s"
    return f"{secs}s"


class StatusSkill(Skill):
    name = "status"
    description = "Mostra versão, tempo ativo e estado dos recursos."
    aliases = ("estado", "versao", "versão")

    def __init__(
        self,
        registry: SkillRegistry,
        config: AegisConfig,
        *,
        mode: str,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._registry = registry
        self._config = config
        self._mode = mode
        self._monotonic = monotonic
        self._started = monotonic()

    def run(self, params: Mapping[str, Any]) -> SkillResult:
        def state(enabled: bool) -> str:
            return "ativado" if enabled else "desativado (fase futura)"

        uptime = format_uptime(self._monotonic() - self._started)
        lines = [
            f"{self._config.general.name} {__version__}, modo {self._mode}",
            f"Python {platform.python_version()}",
            f"Tempo ativo: {uptime}",
            f"Habilidades: {len(self._registry)} ({', '.join(s.name for s in self._registry.skills())})",
            f"Aplicativos permitidos: {len(self._config.apps)}",
            f"Voz: {state(self._config.voice.enabled)}",
            f"IA local: {state(self._config.llm.enabled)}",
        ]
        return SkillResult.success("\n".join(lines), version=__version__, uptime=uptime)
