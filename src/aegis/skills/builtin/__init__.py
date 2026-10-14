"""Lista fechada das habilidades disponíveis nesta versão."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from aegis.config import AegisConfig
from aegis.skills.builtin.abrir import AbrirSkill, Launcher
from aegis.skills.builtin.ajuda import AjudaSkill
from aegis.skills.builtin.hora import HoraSkill
from aegis.skills.builtin.status import StatusSkill
from aegis.skills.registry import SkillRegistry


def build_builtin_registry(
    config: AegisConfig,
    *,
    mode: str,
    clock: Callable[[], datetime],
    launcher: Launcher,
) -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(AjudaSkill(registry))
    registry.register(HoraSkill(clock))
    registry.register(StatusSkill(registry, config, mode=mode))
    registry.register(AbrirSkill(config.apps, launcher=launcher))
    return registry
