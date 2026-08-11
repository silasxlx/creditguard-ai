# Security Policy

This repository is a local synthetic-data PoC, not a production banking service. Do not upload real customer material, credentials or external API responses.

## Reporting a vulnerability

Please do not open a public issue containing secrets or exploit details. Contact the repository owner privately through the GitHub account associated with this repository and include a minimal reproduction, affected version and impact. Remove all credentials from the report.

## Security boundaries

Demo mode is opt-in, tools are read-only and allowlisted, uploads are validated, material text is untrusted, and reports are rendered as safe plain text. See [docs/architecture.md](docs/architecture.md) for the complete model.
