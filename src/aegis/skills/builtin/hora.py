from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from aegis.skills.base import Skill, SkillResult

WEEKDAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)
MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def format_pt_br(moment: datetime) -> str:
    weekday = WEEKDAYS[moment.weekday()]
    month = MONTHS[moment.month - 1]
    return f"{moment:%H:%M} — {weekday}, {moment.day} de {month} de {moment.year}."


class HoraSkill(Skill):
    name = "hora"
    description = "Informa a hora e a data atuais."
    aliases = ("horas", "horário", "data", "dia")

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def run(self, params: Mapping[str, Any]) -> SkillResult:
        now = self._clock()
        return SkillResult.success(format_pt_br(now), iso=now.isoformat(timespec="seconds"))
