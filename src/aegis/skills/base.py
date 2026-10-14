"""Contrato das habilidades e validação de parâmetros."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, ClassVar

from aegis.core.commands import normalize_token

_INT_RE = re.compile(r"^[+-]?\d{1,9}$")


class ParamValidationError(ValueError):
    """Parâmetro ausente ou inválido; a mensagem é exibível ao usuário."""


@dataclass(frozen=True)
class ParamSpec:
    name: str
    description: str
    kind: type = str
    required: bool = True
    choices: tuple[str, ...] = ()
    max_length: int = 64
    min_value: int | None = None
    max_value: int | None = None
    greedy: bool = False
    """Consome todo o texto restante (ex.: 'abrir bloco de notas')."""

    def __post_init__(self) -> None:
        if self.kind not in (str, int):
            raise TypeError(f"Tipo de parâmetro não suportado: {self.kind!r}")


@dataclass(frozen=True)
class SkillResult:
    ok: bool
    message: str
    data: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def success(cls, message: str, **data: Any) -> SkillResult:
        return cls(True, message, MappingProxyType(data))

    @classmethod
    def failure(cls, message: str, **data: Any) -> SkillResult:
        return cls(False, message, MappingProxyType(data))


class Skill(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()
    params: ClassVar[tuple[ParamSpec, ...]] = ()

    @property
    def usage(self) -> str:
        parts = [self.name]
        for spec in self.params:
            parts.append(f"<{spec.name}>" if spec.required else f"[{spec.name}]")
        return " ".join(parts)

    @abstractmethod
    def run(self, params: Mapping[str, Any]) -> SkillResult:
        """Executa a habilidade com parâmetros já validados."""


def bind_params(specs: Sequence[ParamSpec], args: Sequence[str]) -> dict[str, Any]:
    """Associa argumentos posicionais às especificações e valida cada valor."""
    remaining = list(args)
    values: dict[str, Any] = {}
    for spec in specs:
        if spec.greedy:
            raw = " ".join(remaining) or None
            remaining = []
        else:
            raw = remaining.pop(0) if remaining else None
        if raw is None:
            if spec.required:
                raise ParamValidationError(f"Informe o parâmetro '{spec.name}'.")
            continue
        values[spec.name] = _coerce(spec, raw)
    if remaining:
        if not specs:
            raise ParamValidationError("Este comando não aceita parâmetros.")
        raise ParamValidationError(f"Este comando aceita no máximo {len(specs)} parâmetro(s).")
    return values


def _coerce(spec: ParamSpec, raw: str) -> Any:
    if len(raw) > spec.max_length:
        raise ParamValidationError(
            f"O parâmetro '{spec.name}' excede {spec.max_length} caracteres."
        )
    if spec.kind is int:
        if not _INT_RE.match(raw):
            raise ParamValidationError(f"O parâmetro '{spec.name}' deve ser um número inteiro.")
        value = int(raw)
        if spec.min_value is not None and value < spec.min_value:
            raise ParamValidationError(f"O parâmetro '{spec.name}' deve ser ≥ {spec.min_value}.")
        if spec.max_value is not None and value > spec.max_value:
            raise ParamValidationError(f"O parâmetro '{spec.name}' deve ser ≤ {spec.max_value}.")
        return value
    if spec.choices:
        normalized = normalize_token(raw)
        for choice in spec.choices:
            if normalize_token(choice) == normalized:
                return choice
        raise ParamValidationError(
            f"Valor inválido para '{spec.name}'. Opções: {', '.join(spec.choices)}."
        )
    return raw
