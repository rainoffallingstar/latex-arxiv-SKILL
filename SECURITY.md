# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it by opening a GitHub issue or contacting the maintainers directly. Do not disclose the vulnerability publicly until it has been addressed.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.1.x   | Yes       |
| 1.0.x   | No        |
| 0.x     | No        |

## Scope

The primary concern is that this framework generates citation and paper content. Key considerations:

- **Citation integrity**: All citations must be verified before inclusion. The `verify-citation` pipeline in `literature_registry.py` enforces this.
- **No credential storage**: This project does not handle authentication or store credentials.
- **Script execution**: Python scripts run with the user's permissions. Review script code before running in sensitive environments.
