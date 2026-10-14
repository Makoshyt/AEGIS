"""Despacho de comandos para habilidades registradas, com validação de parâmetros."""

from __future__ import annotations

import logging
import time

from aegis.core.commands import CommandError, CommandRequest, InputSource, parse_command
from aegis.skills.base import ParamValidationError, SkillResult, bind_params
from aegis.skills.registry import RegistryError, SkillRegistry

UNKNOWN_COMMAND = "Não conheço esse comando. Digite 'ajuda' para ver o que posso fazer."
INTERNAL_ERROR = "Ocorreu um erro interno ao executar o comando. Os detalhes foram registrados no log."


class Dispatcher:
    def __init__(
        self,
        registry: SkillRegistry,
        *,
        log_command_text: bool = False,
        logger: logging.Logger | None = None,
    ) -> None:
        if not registry.frozen:
            raise RegistryError("O registro de habilidades deve estar congelado antes do uso.")
        self._registry = registry
        self._log_command_text = log_command_text
        self._log = logger or logging.getLogger("aegis.dispatcher")

    def handle_text(self, text: str, source: InputSource = InputSource.TEXT) -> SkillResult:
        try:
            request = parse_command(text, source)
        except CommandError as exc:
            return SkillResult.failure(str(exc))
        return self.dispatch(request)

    def dispatch(self, request: CommandRequest) -> SkillResult:
        if self._log_command_text:
            self._log.info("texto recebido (origem=%s): %s", request.source, request.raw_text)

        skill = self._registry.resolve(request.keyword)
        if skill is None:
            self._log.info("comando não reconhecido (origem=%s)", request.source)
            return SkillResult.failure(UNKNOWN_COMMAND)

        try:
            params = bind_params(skill.params, request.args)
        except ParamValidationError as exc:
            self._log.info("parâmetros inválidos habilidade=%s origem=%s", skill.name, request.source)
            return SkillResult.failure(f"{exc} Uso: {skill.usage}")

        started = time.perf_counter()
        try:
            result = skill.run(params)
        except Exception:
            self._log.exception("falha na habilidade=%s", skill.name)
            return SkillResult.failure(INTERNAL_ERROR)
        if not isinstance(result, SkillResult):
            self._log.error("habilidade=%s retornou tipo inválido", skill.name)
            return SkillResult.failure(INTERNAL_ERROR)

        self._log.info(
            "habilidade=%s origem=%s ok=%s duracao_ms=%.1f",
            skill.name,
            request.source,
            result.ok,
            (time.perf_counter() - started) * 1000,
        )
        return result
