# Security Guidelines

## Purpose
Capture the repository-specific security rules and operational boundaries for Lobsterhook.

## Authentication and Authorization
- Outbound webhook authentication is Bearer-token based and scoped per account configuration.
- Keep tokens in environment variables or external files when possible. Inline TOML tokens are supported but are the least desirable option.

## Input Validation
- Validate TOML config values before runtime work starts.
- Treat Himalaya JSON output and raw message content as untrusted input; parse defensively and keep failures local to the affected message or job.

## Secrets and Environment Variables
- Do not store bearer tokens in SQLite job payloads or event payload files.
- Avoid committing `lobsterhook.toml` with real credentials. The repository only tracks [`lobsterhook.example.toml`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/lobsterhook.example.toml).

## Data Protection
- Raw `.eml` files may contain sensitive mail content and attachments. Keep `data/` out of git and treat it as private runtime state.
- Send normalized JSON to downstream webhooks only over HTTPS unless a local-only receiver explicitly justifies plain HTTP.

## Risky Operations
- Do not use `himalaya message read` without `--preview` in future tooling, because it can mutate mailbox seen state.
- Do not expand webhook payloads to include unneeded raw message content unless a receiver genuinely requires it.

## Security Review Checklist
- [ ] Secret sources remain outside queued job payloads
- [ ] New config inputs are validated explicitly
- [ ] Raw message storage paths remain git-ignored
- [ ] Webhook delivery changes preserve least-privilege account scoping
