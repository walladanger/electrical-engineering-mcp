# Electrical Engineering MCP

A local, open-source MCP server for deterministic electrical calculations. The first release covers balanced AC power/current, approximate voltage drop, induction motor nameplate relationships, ideal transformer nameplate currents, and ideal power factor correction. It returns units, assumptions, equations and limitations with every calculation.

**This release does not size conductors or protective devices, perform NEC/IEC/CEC compliance checks, or run short-circuit studies.** Those need separate standards data and network models. See [SPEC.md](SPEC.md) for the contract and staged direction.

## Install and run on Windows

Install [Python 3.11 or newer](https://www.python.org/downloads/) with the Python launcher enabled. In PowerShell inside this repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\electrical-engineering-mcp.exe
```

If Python 3.12 is not installed, replace `py -3.12` with the installed Python 3.11+ launcher selection. The last command starts a stdio MCP process; it waits silently for a client and is not a graphical program.

Point a local MCP client's stdio server configuration to the **absolute path** of `.venv\Scripts\electrical-engineering-mcp.exe`, with no arguments. The client launches it on demand. No API key, Wolfram account, or network connection is needed at runtime. A local stdio server cannot be called directly by a cloud-only ChatGPT connector; remote access would require a separately hosted, authenticated transport.

For example, in PowerShell, replace `C:\path\to\electrical-engineering-mcp` with the repository's actual location:

```powershell
codex mcp add electrical-engineering -- "C:\path\to\electrical-engineering-mcp\.venv\Scripts\electrical-engineering-mcp.exe"
codex mcp list
claude mcp add --transport stdio electrical-engineering -- "C:\path\to\electrical-engineering-mcp\.venv\Scripts\electrical-engineering-mcp.exe"
claude mcp list
```

These commands register a **local** MCP server with Codex and Claude Code. Restart the client if its tool list was already loaded. The command syntax follows the [Codex MCP guide](https://developers.openai.com/codex/mcp) and [Claude Code MCP guide](https://code.claude.com/docs/en/mcp).

## Develop and test

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

For Linux/macOS, use `python3 -m venv .venv`, `.venv/bin/python -m pip install -e '.[test]'` and `.venv/bin/python -m pytest -q`.

The results are engineering estimates with explicit assumptions. Verify input data and use the applicable adopted code, equipment instructions, and qualified design review for safety-critical decisions.
