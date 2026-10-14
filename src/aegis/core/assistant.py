"""Fachada do núcleo: ponto único de entrada para texto hoje e voz no futuro."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from aegis.config import AegisConfig
from aegis.core.commands import InputSource
from aegis.core.dispatcher import Dispatcher
from aegis.skills.base import SkillResult
from aegis.skills.builtin import build_builtin_registry
from aegis.skills.builtin.abrir import Launcher, default_launcher


class Assistant:
    def __init__(
        self,
        config: AegisConfig,
        *,
        mode: str,
        clock: Callable[[], datetime] = datetime.now,
        launcher: Launcher = default_launcher,
    ) -> None:
        self.config = config
        self.registry = build_builtin_registry(config, mode=mode, clock=clock, launcher=launcher)
        self.registry.freeze()
        self.dispatcher = Dispatcher(
            self.registry, log_command_text=config.logging.log_command_text
        )

    def submit(self, text: str, source: InputSource = InputSource.TEXT) -> SkillResult:
        return self.dispatcher.handle_text(text, source)
