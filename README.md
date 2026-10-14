# AEGIS IA

Assistente pessoal local para Windows: janela discreta, ícone na bandeja e atalho global.

**Fase 1 (atual):** fundação modular, comandos por texto, habilidades registradas com
parâmetros validados, logging com mascaramento de dados sensíveis e testes automatizados.
Voz, palavra de ativação e integração com LLM (Ollama) virão em fases posteriores.

## Requisitos

- Windows 11
- Python **3.12** (o launcher `py` desta máquina usa o 3.13 por padrão; sempre use `py -3.12`)

## Instalação

```powershell
cd C:\Makoshyt\AEGIS
py -3.12 -m venv .venv
.venv\Scripts\python -c "import sys; print(sys.version)"   # deve mostrar 3.12.x
.venv\Scripts\python -m pip install -e ".[dev]"
```

## Execução

```powershell
.venv\Scripts\python -m aegis          # janela + bandeja + Ctrl+Alt+A
.venv\Scripts\pythonw -m aegis         # mesmo, sem janela de console
.venv\Scripts\python -m aegis --cli    # modo texto no terminal
```

- Fechar a janela apenas a oculta; use **Sair** no menu do ícone da bandeja para encerrar.
- No Windows 11 o ícone pode ficar no menu de ícones ocultos (seta `^` da barra de tarefas).
- Se `Ctrl+Alt+A` já estiver em uso por outro programa, o AEGIS continua funcionando e
  mostra um aviso na barra de status. O atalho pode ser alterado em `[hotkey]`.
- Logs: `var\logs\aegis.log` (rotação automática; segredos, e-mails e nome de usuário mascarados).

## Comandos disponíveis

| Comando | Exemplo | Descrição |
|---|---|---|
| `ajuda [comando]` | `ajuda abrir` | Lista ou detalha os comandos |
| `hora` | `horário` | Hora e data atuais |
| `status` | `status` | Versão, tempo ativo, habilidades |
| `abrir <aplicativo>` | `abrir bloco de notas` | Abre um aplicativo **da lista permitida** |

## Configuração

`config/aegis.default.toml` contém os valores padrão. Para personalizar, crie
`config/aegis.local.toml` (ignorado pelo Git) apenas com as chaves a alterar, por exemplo:

```toml
[hotkey]
sequence = "Ctrl+Alt+Space"   # teclas suportadas: A–Z, 0–9, F1–F24

[apps.paint]
label = "Paint"
path = 'C:\Windows\System32\mspaint.exe'
```

## Testes

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
```

## Segurança

- O texto do usuário **nunca** é executado nem repassado a um shell: ele só seleciona uma
  habilidade registrada, cujos parâmetros são validados.
- A lista de habilidades é fechada e congelada na inicialização.
- `abrir` inicia somente o caminho `.exe` absoluto configurado, sem argumentos.
- `tests/test_security_guards.py` analisa o código de produção (AST) em busca de
  `subprocess`, `os.system`, `eval`, `exec`, `QProcess` etc., e executa entradas maliciosas
  contra o núcleo real verificando que nenhuma função de execução é acionada.
- Sem rede, sem privilégios de administrador, sem alterações no Windows.

## Estrutura

```
src/aegis/
  __main__.py        ponto de entrada
  app.py             composição da aplicação desktop (início/encerramento, instância única)
  cli.py             modo texto
  config.py          configuração centralizada e validada
  logging_setup.py   logging com mascaramento
  core/              núcleo independente da interface (comandos, despacho, fachada)
  skills/            contrato, registro fechado e habilidades embutidas
  ui/                janela, bandeja e atalho global (PySide6)
tests/               testes automatizados (pytest + pytest-qt)
```
