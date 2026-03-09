# Changelog

All notable changes to SkillForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of SkillForge CLI
- Support for 6 skill templates (github-api, file-ops, mcp-integration, web-search, loom-query, blank)
- LLM-as-judge testing framework with YAML test cases
- Built-in security scanner with 4 core rules
- Cross-platform compatibility checking (ClawHub, Claude Code, Cursor, Windsurf)
- Quality scoring and benchmarking
- Ed25519 provenance signing for published skills
- GitHub Actions workflow integration

### Security
- SF001: Dynamic fetch detection
- SF002: Hardcoded credential detection
- SF003: Prompt injection detection
- SF004: Undeclared network endpoint detection
- Snyk agent-scan integration

## [0.1.0] - 2026-03-09

### Added
- `skillforge init` - Scaffold new skills from templates
- `skillforge test` - LLM-as-judge evaluation framework
- `skillforge scan` - Security scanner with built-in rules
- `skillforge compat` - Cross-platform compatibility matrix
- `skillforge bench` - Quality scoring and benchmarking
- `skillforge publish` - Sign and publish to registries
- Complete Pydantic schema definitions
- Rich CLI output and progress indicators
- Comprehensive test suite
- Documentation and examples

### Supported Platforms
- ClawHub (OpenClaw)
- Claude Code (Anthropic)
- Cursor (Cursor AI)
- Windsurf (Codeium)

### Dependencies
- Python 3.12+
- Typer for CLI framework
- Rich for terminal output
- Pydantic for data validation
- LiteLLM for LLM calls
- PyNaCl for Ed25519 signing
- HTTPX for HTTP requests

### Documentation
- Complete README with quick start guide
- Contributing guidelines
- Security policy
- API documentation (inline)

---

## [Future Roadmap]

### Planned Features
- [ ] VS Code extension
- [ ] Rust benchmark runner
- [ ] Real-time file watching (`skillforge watch`)
- [ ] Advanced security rules
- [ ] More skill templates
- [ ] Integration with more platforms
- [ ] Web dashboard for skill management
- [ ] Team collaboration features

### Platform Support
- [ ] Full Claude Code publishing
- [ ] Full Cursor publishing  
- [ ] Full Windsurf publishing
- [ ] Additional platform integrations

### Performance & Reliability
- [ ] Parallel test execution
- [ ] Caching for test results
- [ ] Incremental scanning
- [ ] Better error recovery
- [ ] Performance profiling tools

---

*For release announcements and updates, follow [@skillforge](https://github.com/ddevilz/skillforge).*
