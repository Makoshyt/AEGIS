"""Proteções contra execução arbitrária.

1. Análise estática (AST) dos módulos de produção: detecta *imports e chamadas reais*, não
   simples ocorrências de nomes em strings ou comentários.
2. Testes de comportamento: entradas maliciosas passam pelo núcleo real com as funções de
   execução do sistema substituídas por gravadores; nenhuma pode ser acionada indevidamente.
"""

from __future__ import annotations

import ast
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

import aegis
from aegis.core.assistant import Assistant

from conftest import make_config

SRC_ROOT = Path(aegis.__file__).resolve().parent

FORBIDDEN_MODULES = {
    "subprocess", "pty", "pexpect", "multiprocessing", "runpy", "code", "codeop",
    "pickle", "marshal", "shelve", "importlib", "webbrowser",
}
FORBIDDEN_BUILTINS = {"eval", "exec", "compile", "__import__", "breakpoint"}
FORBIDDEN_OS_PREFIXES = ("system", "popen", "exec", "spawn", "posix_spawn", "fork", "kill")
FORBIDDEN_QT_NAMES = {"QProcess", "QDesktopServices", "QLibrary", "QPluginLoader"}

# Exceções explícitas e justificadas: (módulo, recurso).
ALLOWED = {
    ("aegis.skills.builtin.abrir", "os.startfile"),  # executável fixo da lista permitida
    ("aegis.ui.hotkey", "ctypes"),  # RegisterHotKey/UnregisterHotKey em user32
}


@dataclass(frozen=True)
class Violation:
    module: str
    feature: str
    line: int


def _module_name(path: Path) -> str:
    rel = path.relative_to(SRC_ROOT.parent).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    return ".".join(parts)


def scan_source(source: str, module: str) -> list[Violation]:
    """Retorna usos reais de recursos perigosos em um módulo."""
    tree = ast.parse(source)
    found: list[Violation] = []
    os_aliases = {"os"}

    def add(feature: str, node: ast.AST) -> None:
        if (module, feature) not in ALLOWED:
            found.append(Violation(module, feature, getattr(node, "lineno", 0)))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FORBIDDEN_MODULES:
                    add(root, node)
                if root == "ctypes":
                    add("ctypes", node)
                if alias.name == "os":
                    os_aliases.add(alias.asname or "os")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in FORBIDDEN_MODULES:
                add(root, node)
            if root == "ctypes":
                add("ctypes", node)
            for alias in node.names:
                if root == "os" and alias.name.startswith(FORBIDDEN_OS_PREFIXES + ("startfile",)):
                    add(f"os.{alias.name}", node)
                if alias.name in FORBIDDEN_QT_NAMES:
                    add(alias.name, node)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTINS:
                add(node.func.id, node)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in os_aliases:
                if node.attr.startswith(FORBIDDEN_OS_PREFIXES) or node.attr == "startfile":
                    add(f"os.{node.attr}", node)
            if node.attr in FORBIDDEN_QT_NAMES:
                add(node.attr, node)
        elif isinstance(node, ast.Constant) and node.value == "startfile":
            # getattr(os, "startfile") também conta como uso do recurso.
            add("os.startfile", node)
    return found


def _production_modules() -> list[tuple[str, str]]:
    return [
        (_module_name(p), p.read_text(encoding="utf-8")) for p in sorted(SRC_ROOT.rglob("*.py"))
    ]


def test_scanner_covers_all_production_modules():
    names = {name for name, _ in _production_modules()}
    assert {"aegis.app", "aegis.core.dispatcher", "aegis.skills.builtin.abrir"} <= names


def test_production_code_has_no_forbidden_execution():
    violations = [v for name, src in _production_modules() for v in scan_source(src, name)]
    assert violations == []


def test_ctypes_only_loads_user32():
    source = (SRC_ROOT / "ui" / "hotkey.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") in (
            "WinDLL", "CDLL", "LoadLibrary", "OleDLL",
        ):
            assert isinstance(node.args[0], ast.Constant) and node.args[0].value == "user32"


@pytest.mark.parametrize(
    "snippet, feature",
    [
        ("import subprocess", "subprocess"),
        ("from subprocess import run", "subprocess"),
        ("import os\nos.system('x')", "os.system"),
        ("import os as o\no.popen('x')", "os.popen"),
        ("from os import execv", "os.execv"),
        ("eval('1+1')", "eval"),
        ("exec(code)", "exec"),
        ("__import__('os')", "__import__"),
        ("import importlib\nimportlib.import_module('x')", "importlib"),
        ("from PySide6.QtCore import QProcess", "QProcess"),
        ("import os\nos.startfile('x')", "os.startfile"),
    ],
)
def test_scanner_detects_violations(snippet, feature):
    assert [v.feature for v in scan_source(snippet, "aegis.fake")] == [feature]


def test_scanner_ignores_names_in_strings_and_comments():
    snippet = (
        "# nunca use subprocess nem os.system aqui\n"
        "MSG = 'eval e exec são proibidos; subprocess também'\n"
        "def evaluate(x):\n    return x\n"
        "evaluate(1)\n"
    )
    assert scan_source(snippet, "aegis.fake") == []


# --- Testes de comportamento ------------------------------------------------------------------


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


@pytest.fixture
def guarded(tmp_path, monkeypatch):
    fake_exe = tmp_path / "fake_bloco.exe"
    fake_exe.write_bytes(b"")
    config = make_config(
        tmp_path, f"[apps.bloco]\nlabel = 'Bloco de Notas'\npath = '{fake_exe}'\n"
    )
    recorders = {
        "startfile": Recorder(),
        "system": Recorder(),
        "popen": Recorder(),
        "Popen": Recorder(),
        "run": Recorder(),
    }
    monkeypatch.setattr(os, "startfile", recorders["startfile"], raising=False)
    monkeypatch.setattr(os, "system", recorders["system"])
    monkeypatch.setattr(os, "popen", recorders["popen"])
    monkeypatch.setattr(subprocess, "Popen", recorders["Popen"])
    monkeypatch.setattr(subprocess, "run", recorders["run"])
    # Assistente com o launcher padrão real (que usa os.startfile).
    return Assistant(config, mode="teste"), recorders, str(fake_exe)


MALICIOUS_INPUTS = [
    "abrir cmd",
    r"abrir C:\Windows\System32\cmd.exe",
    "abrir powershell -c whoami",
    "abrir bloco && calc",
    "abrir bloco; del /q *",
    "abrir bloco | calc",
    "abrir notepad.exe C:\\segredo.txt",
    "abrir ../../Windows/System32/cmd.exe",
    "abrir $(calc)",
    "abrir `calc`",
    "hora; shutdown /s /t 0",
    "status && format c:",
    "ajuda & calc",
    "cmd /c calc",
    "powershell Remove-Item -Recurse C:\\",
    "python -c \"import os\"",
    "__import__('os').system('calc')",
    "eval 1+1",
]


@pytest.mark.parametrize("text", MALICIOUS_INPUTS)
def test_malicious_input_never_executes(guarded, text):
    assistant, recorders, _ = guarded
    assistant.submit(text)
    assert all(not r.calls for r in recorders.values()), {k: r.calls for k, r in recorders.items()}


def test_allowed_app_launches_exact_configured_path_without_args(guarded):
    assistant, recorders, exe = guarded
    result = assistant.submit("abrir o Bloco de Notas")
    assert result.ok
    assert recorders["startfile"].calls == [((exe,), {})]
    assert all(not recorders[k].calls for k in ("system", "popen", "Popen", "run"))


def test_registry_cannot_be_extended_at_runtime(guarded):
    from aegis.skills.registry import RegistryError

    assistant, _, _ = guarded
    skill = assistant.registry.resolve("hora")
    with pytest.raises(RegistryError):
        assistant.registry.register(skill)
