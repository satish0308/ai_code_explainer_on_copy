# Auto Code Explainer - Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please follow these steps:

1. **Do NOT create a public GitHub issue** - This could expose the vulnerability
2. **Email us directly** with details about the vulnerability
3. Provide:
   - Description of the issue
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes

## Security Practices

This project follows security best practices:

- **No API keys stored in code** - Configuration is stored in user's home directory
- **Environment variables** - Used for sensitive configuration
- **Input validation** - Clipboard content is validated before processing
- **Dependency updates** - Regular updates to dependencies via Dependabot

## Disclosure Process

1. Report vulnerability
2. We'll acknowledge receipt within 48 hours
3. We'll work to fix the issue
4. Once fixed, we'll:
   - Publish a security advisory
   - Release a patched version
   - Credit the reporter (with permission)
