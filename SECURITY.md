# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

### How to Report

If you discover a security vulnerability, please report it privately:

1. **Email**: jadhavom263@gmail.com

Please include:
- Detailed description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Any suggested fixes (if available)

### Response Timeline

- **Initial response**: Within 48 hours
- **Detailed assessment**: Within 7 days
- **Patch release**: Within 14 days (for critical vulnerabilities)
- **Public disclosure**: After patch is released, or with maintainer approval

### Severity Levels

- **Critical**: Remote code execution, data exfiltration, privilege escalation
- **High**: Security bypasses, authentication issues
- **Medium**: Information disclosure, denial of service
- **Low**: Minor security issues, hardening opportunities

### Security Features

SkillForge includes several built-in security features:

- **SF001** - Dynamic fetch detection
- **SF002** - Hardcoded credential detection  
- **SF003** - Prompt injection detection
- **SF004** - Undeclared network endpoint detection
- **Ed25519** - Provenance signing for all published skills

### Security Scanning

All skills are automatically scanned before publishing:

```bash
skillforge scan  # Built-in rules + Snyk integration
```

### Responsible Disclosure Program

We believe in responsible disclosure and will work with researchers to:

1. Acknowledge and validate reports promptly
2. Provide credit for discovered vulnerabilities
3. Coordinate disclosure timelines
4. Consider bounty payments for critical issues

### Security Best Practices for Skill Authors

1. **Never hardcode credentials** - use environment variables
2. **Declare all network endpoints** in `skill.json`
3. **Avoid dynamic code execution** patterns
4. **Review tool descriptions** for prompt injection risks
5. **Sign your skills** with Ed25519 keys
6. **Run security scans** before publishing
