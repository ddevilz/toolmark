# SkillForge 🔨

> **ESLint + Jest + npm publish — for AI Agent Skills.**

Build, test, scan, and ship skills across **OpenClaw/ClawHub**, **Claude Code**, **Cursor**, and **Windsurf** — from a single CLI.

[![PyPI](https://img.shields.io/pypi/v/skillforge)](https://pypi.org/project/skillforge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/ddevilz/skillforge/actions/workflows/skillforge.yml/badge.svg)](https://github.com/ddevilz/skillforge/actions)

---

## Why SkillForge?

13,000+ skills are published on ClawHub. **13% contain critical security flaws** *(Snyk ToxicSkills Report, Feb 2026)*. Skills break silently on platforms other than the one they were tested on. There is no `pytest` for agent skills — until now.

```
skillforge init my-skill --template github-api
skillforge test          # LLM-as-judge evaluation
skillforge scan          # prompt injection, dynamic fetch, credential leaks
skillforge compat        # check all 4 platforms at once
skillforge publish       # sign with Ed25519, push to ClawHub + Claude Code
```

---

## Install

```bash
pip install skillforge
```

Requires Python 3.12+.

---

## Quick Start

```bash
# 1. Scaffold
skillforge init my-github-skill --template github-api

# 2. Edit SKILL.md and tests/
cd my-github-skill

# 3. Test
ANTHROPIC_API_KEY=sk-ant-... skillforge test

# 4. Scan
skillforge scan

# 5. Check platform compatibility
skillforge compat

# 6. Publish
skillforge publish --platforms clawhub,claude-code
```

---

## Commands

| Command               | What it does                                              |
|-----------------------|-----------------------------------------------------------|
| `skillforge init`     | Scaffold a new skill from a template                      |
| `skillforge test`     | LLM-as-judge evaluation against YAML test cases           |
| `skillforge scan`     | Security scanner (prompt injection, dynamic fetch, creds) |
| `skillforge compat`   | Cross-platform compatibility check (4 platforms)          |
| `skillforge bench`    | Benchmark latency, tokens, compute quality score (0–100)  |
| `skillforge publish`  | Sign with Ed25519, publish to configured registries       |

---

## Templates

```bash
skillforge init my-skill --template github-api      # GitHub REST API wrapper
skillforge init my-skill --template file-ops         # Local filesystem skill
skillforge init my-skill --template mcp-integration  # Wraps an MCP server tool
skillforge init my-skill --template web-search       # Search API skill
skillforge init my-skill --template loom-query       # Loom knowledge graph skill
skillforge init my-skill --template blank            # Minimal scaffold
```

---

## Test Cases (YAML)

```yaml
# tests/test_search.yaml
- id: search_open_prs
  input: "find my open pull requests"
  expect_invoked: true
  expect_tool: search_pull_requests
  expect_params:
    state: open
    assignee: "@me"
  tolerance: fuzzy     # strict | fuzzy | invoked
  tags: [smoke]
```

Run: `skillforge test --tags smoke`

---

## Security

SkillForge catches:
- **SF001** — Dynamic fetch (`curl | bash`, `eval(fetch(...))`)
- **SF002** — Hardcoded credentials (API keys, passwords)
- **SF003** — Prompt injection phrases in tool descriptions
- **SF004** — Undeclared network endpoints
- **SNYK-*** — 138 rules via Snyk agent-scan (if installed)

---

## Provenance Signing

Every published skill is signed with Ed25519:

```bash
skillforge keygen              # creates ~/.skillforge/signing.key
skillforge publish --sign      # signs + publishes
skillforge verify my-skill     # verify any published skill
```

---

## GitHub Actions

Every `skillforge init` project includes a ready-to-use workflow:

```yaml
# .github/workflows/skillforge.yml — already in your project
- skillforge compat    # platform check
- skillforge scan      # security gate
- skillforge test      # LLM evaluation (needs ANTHROPIC_API_KEY secret)
```

---

## Quality Leaderboard

See how your skill ranks: **[skillforge.dev/leaderboard](https://skillforge.dev/leaderboard)**

Quality Score = test pass rate (50%) + security score (30%) + compat score (20%).

---

## Roadmap

- [x] `init` — scaffold with 6 templates
- [x] `test` — LLM-as-judge evaluation
- [x] `scan` — built-in security rules + Snyk integration
- [x] `compat` — 4-platform compatibility matrix
- [x] `bench` — composite quality score
- [x] `publish` — Ed25519 signing + ClawHub
- [ ] `watch` — re-run tests on save
- [ ] VS Code extension
- [ ] Rust benchmark runner
- [ ] Claude Code + Cursor + Windsurf publish

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We always have [good first issues](https://github.com/ddevilz/skillforge/issues?q=label%3A%22good+first+issue%22).

## License

MIT — see [LICENSE](LICENSE).

---

*Built by [@ddevilz](https://github.com/ddevilz) as part of the [Loom](https://github.com/ddevilz/loom) AI tooling ecosystem.*
