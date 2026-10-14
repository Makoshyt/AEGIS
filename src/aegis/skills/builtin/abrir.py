"""Abertura de aplicativos restrita a uma lista permitida.

Somente o caminho absoluto configurado em ``[apps]`` é iniciado, sem argumentos.
Nada do texto do usuário chega ao processo iniciado.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from typing import Any

from aegis.config import AllowedApp
from aegis.core.commands import normalize_phrase
from aegis.skills.base import ParamSpec, Skill, SkillResult

Launcher = Callable[[str], None]
_ARTICLES = frozenset({"o", "a", "os", "as"})
_log = logging.getLogger("aegis.skills.abrir")


def default_launcher(path: str) -> None:
    """Inicia um executável fixo da lista permitida via ShellExecute, sem argumentos."""
    startfile = getattr(os, "startfile", None)
    if startfile is None:
        raise OSError("Abrir aplicativos só é suportado no Windows.")
    startfile(path)


class AbrirSkill(Skill):
    name = "abrir"
    description = "Abre um aplicativo da lista permitida."
    aliases = ("abra", "abre", "iniciar", "inicie")
    params = (ParamSpec("aplicativo", "Nome do aplicativo permitido", greedy=True, max_length=60),)

    def __init__(
        self,
        apps: Mapping[str, AllowedApp],
        *,
        launcher: Launcher = default_launcher,
        path_exists: Callable[[str], bool] = os.path.isfile,
    ) -> None:
        self._apps = apps
        self._launcher = launcher
        self._path_exists = path_exists

    def _match(self, query: str) -> AllowedApp | None:
        words = normalize_phrase(query).split()
        if words and words[0] in _ARTICLES:
            words = words[1:]
        wanted = " ".join(words)
        for app in self._apps.values():
            if wanted in (normalize_phrase(app.key), normalize_phrase(app.label)):
                return app
        return None

    def run(self, params: Mapping[str, Any]) -> SkillResult:
        if not self._apps:
            return SkillResult.failure("Nenhum aplicativo está liberado na configuração.")

        app = self._match(params["aplicativo"])
        if app is None:
            allowed = ", ".join(f"{a.key} ({a.label})" for a in self._apps.values())
            return SkillResult.failure(f"Esse aplicativo não está na lista permitida: {allowed}.")

        if not self._path_exists(app.path):
            _log.warning("executável não encontrado para app=%s", app.key)
            return SkillResult.failure(f"O executável configurado para {app.label} não foi encontrado.")

        try:
            self._launcher(app.path)
        except OSError:
            _log.exception("falha ao abrir app=%s", app.key)
            return SkillResult.failure(f"Não foi possível abrir {app.label}.")

        _log.info("aplicativo aberto app=%s", app.key)
        return SkillResult.success(f"Abrindo {app.label}.", app=app.key)
