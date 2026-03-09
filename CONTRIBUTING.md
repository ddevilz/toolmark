# Contributing to SkillForge

Thank you for your interest in contributing to SkillForge! This document provides comprehensive guidelines for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style & Quality](#code-style--quality)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git
- GitHub account (for contributions)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/ddevilz/skillforge.git
cd skillforge

# Set up development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests to verify setup
pytest tests/ -v
```

## Development Setup

### Environment Variables

For development, you may want to set:

```bash
export ANTHROPIC_API_KEY=sk-ant-...  # For LLM testing
export GITHUB_TOKEN=ghp_...          # For GitHub API tests
export SKILLFORGE_DEV=1               # Enable dev features
```

### Development Tools

SkillForge uses the following tools:

- **Ruff** - Linting and formatting
- **MyPy** - Type checking
- **Pytest** - Testing framework
- **Pre-commit** - Git hooks (optional)

Install pre-commit hooks:

```bash
pre-commit install
```

## How to Contribute

### Types of Contributions

We welcome contributions in many forms:

1. **Bug Reports** - Found an issue? Please report it!
2. **Feature Requests** - Have an idea? We'd love to hear it!
3. **Code Contributions** - Fix bugs, add features, improve documentation
4. **Skill Templates** - Create new skill templates
5. **Security Improvements** - Help make skills more secure
6. **Documentation** - Improve docs, examples, tutorials

### Good First Issues

Start here! Look for issues labeled `good first issue`:

https://github.com/ddevilz/skillforge/issues?q=label%3A%22good+first+issue%22

Examples of good first issues:
- Add a new skill template
- Improve error messages
- Add a new security rule
- Write more test cases
- Improve documentation

### Finding Issues to Work On

- **Bugs**: Issues labeled `bug`
- **Features**: Issues labeled `enhancement`
- **Documentation**: Issues labeled `documentation`
- **Security**: Issues labeled `security`

## Code Style & Quality

### Formatting and Linting

We use Ruff for consistent formatting:

```bash
ruff check .          # Check for issues
ruff format .         # Format code
ruff check --fix .    # Auto-fix issues
```

### Type Checking

```bash
mypy skillforge/      # Type check the codebase
```

### Code Guidelines

1. **Follow PEP 8** - Python style guide
2. **Use type hints** - All functions should have type annotations
3. **Write docstrings** - Use Google-style docstrings
4. **Keep functions small** - Single responsibility principle
5. **Use meaningful names** - Clear, descriptive variable and function names

### Example Code Style

```python
"""Google-style docstring.

Args:
    skill_dir: Path to the skill directory.
    strict: Whether to fail on medium severity findings.

Returns:
    ScanReport containing all findings.

Raises:
    FileNotFoundError: If skill.json is not found.
    ValidationError: If manifest is invalid.
"""
def scan_skill(skill_dir: Path, strict: bool = False) -> ScanReport:
    """Scan a skill for security issues."""
    manifest = load_manifest(skill_dir)
    findings = list(_run_scan_rules(manifest, skill_dir))
    
    if strict and any(f.severity == Severity.MEDIUM for f in findings):
        raise SecurityError("Medium severity findings found in strict mode")
    
    return ScanReport(manifest=manifest, findings=findings)
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=skillforge tests/

# Run specific test file
pytest tests/test_scan.py -v

# Run tests matching a pattern
pytest tests/ -k "test_scan" -v
```

### Writing Tests

1. **Unit Tests** - Test individual functions and classes
2. **Integration Tests** - Test command-line interfaces and external APIs
3. **Fixtures** - Use pytest fixtures for common setup

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_scan.py          # Scan command tests
├── test_test.py          # Test command tests
├── test_publish.py       # Publish command tests
└── test_utils.py         # Utility function tests
```

### Example Test

```python
def test_scan_finds_hardcoded_creds(tmp_path: Path):
    """Test that scan finds hardcoded credentials."""
    skill_json = {
        "name": "test-skill",
        "version": "0.1.0",
        "author": "test",
        "description": "Test skill",
        "tools": []
    }
    
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "skill.json").write_text(json.dumps(skill_json))
    (skill_dir / "SKILL.md").write_text("API_KEY = 'sk-1234567890abcdef'")
    
    findings = list(_scan_hardcoded_creds("API_KEY = 'sk-1234567890abcdef'", "SKILL.md"))
    
    assert len(findings) == 1
    assert findings[0].rule_id == "SF002"
    assert findings[0].severity == Severity.CRITICAL
```

### Integration Tests

Tests that require external APIs are marked with `@pytest.mark.integration`:

```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
def test_llm_judge_integration():
    """Test LLM judge with real API call."""
    # Integration test code here
    pass
```

## Documentation

### Types of Documentation

1. **Code Documentation** - Docstrings and comments
2. **User Documentation** - README, guides, tutorials
3. **API Documentation** - Auto-generated from docstrings
4. **Developer Documentation** - Architecture, contributing guide

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add screenshots where helpful
- Keep documentation up to date with code changes

### Documentation Structure

```
docs/                    # If you add a docs folder
├── user-guide/         # User documentation
├── api-reference/       # API documentation
├── tutorials/          # Step-by-step tutorials
└── developer-guide/    # Developer documentation
```

## Submitting Changes

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** following the guidelines above
4. **Add tests** for your changes
5. **Run the test suite**: `pytest tests/`
6. **Check code quality**: `ruff check . && mypy skillforge/`
7. **Commit your changes**: `git commit -m "Add amazing feature"`
8. **Push to your fork**: `git push origin feature/amazing-feature`
9. **Open a Pull Request**

### Pull Request Guidelines

- **Clear title and description** - Explain what you changed and why
- **Link to issues** - Reference any related issues with `#123`
- **Add screenshots** - For UI changes
- **Test thoroughly** - Ensure all tests pass
- **Update documentation** - Keep docs in sync with code

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(scan): add credential detection for AWS keys
fix(publish): handle timeout during upload
docs(readme): add quick start example
test(scan): add tests for prompt injection detection
```

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Release Checklist

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with changes
3. **Run full test suite**: `pytest tests/ --cov=skillforge`
4. **Check code quality**: `ruff check . && mypy skillforge/`
5. **Build package**: `python -m build`
6. **Tag release**: `git tag v0.1.0`
7. **Push tag**: `git push origin v0.1.0`
8. **Publish to PyPI**: `python -m twine upload dist/*`

## Getting Help

### Ways to Get Help

1. **GitHub Issues** - Report bugs or request features
2. **GitHub Discussions** - Ask questions, share ideas
3. **Discord Community** - Real-time chat (if available)
4. **Email** - For security issues or private questions

### Community Guidelines

- Be respectful and inclusive
- Help newcomers learn
- Share knowledge generously
- Focus on constructive feedback

## Recognition

Contributors are recognized in several ways:

- **GitHub Contributors** - Listed in repository
- **CHANGELOG.md** - Mentioned in release notes
- **README.md** - Top contributors acknowledged
- **Community Spotlight** - Featured in blog posts/social media

Thank you for contributing to SkillForge! 🎉

---

For questions about contributing, reach out to us at:
- GitHub Issues: https://github.com/ddevilz/skillforge/issues
- Email: contribute@skillforge.dev
