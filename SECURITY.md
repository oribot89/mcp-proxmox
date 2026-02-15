# Security Policy

## Incident Report: Exposed API Tokens (2026-02-15)

### Summary
On 2026-02-15, backup files containing old API tokens were discovered in git history. The issue was immediately remediated.

### What Happened
- **Discovery**: Found `.env_2025-09-19_20-15-03.bkp` and `.env_2025-10-16_16-39-24.bkp` in public repository
- **Exposure**: Old API tokens visible in git history (accessible to anyone)
- **Risk Level**: LOW - Tokens were old backups; current token was NOT exposed
- **Status**: REMEDIATED on 2026-02-15

### Exposed Credentials (OLD - REVOKED)
These tokens should be **deleted from Proxmox immediately**:
- `root@pam!mcp-proxmox` (Sep 2025 backup)
- `root@pam!mcp-proxmox-server` (Oct 2025 backup)

### Current Credentials (SAFE)
Current token remains secure and was NOT compromised:
- `root@pam!mcp-proxmox` (current, different secret)

### Remediation Completed
✅ **2026-02-15 22:16 UTC** - Git history scrubbed
- Ran `git filter-branch` to remove all .env*.bkp files
- Cleaned reflog and garbage collected
- Force pushed cleaned history to GitHub
- Repository history rewritten (17 commits processed)

✅ **2026-02-15 22:19 UTC** - GitHub security hardening
- Enabled secret scanning on repository
- Updated .gitignore to prevent future .env commits

### Reporting Vulnerabilities

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email security details to: `oribot@edinprint3d.co.uk`
3. Include:
   - Type of vulnerability
   - Affected component
   - Steps to reproduce
   - Suggested fix (if available)
4. We will respond within 48 hours

### Best Practices

#### For Contributors
- Never commit `.env` files (add to .gitignore)
- Use environment variables for secrets
- Use pre-commit hooks to catch secrets
- Review commits before pushing

#### For Deployers
- Use GitHub secrets for CI/CD authentication
- Rotate API tokens every 90 days
- Enable secret scanning on all repositories
- Monitor logs for unauthorized access

#### For Maintainers
- Regular security audits of git history
- Enable GitHub's secret scanning feature
- Use branch protection rules
- Require code review before merge

### Secret Scanning

This repository has **secret scanning enabled**:
- Automatic detection of exposed credentials
- Push protection prevents commits with secrets
- Alerts sent to repository administrators

### Token Rotation Schedule

- **Current token rotation**: Every 90 days
- **Last rotated**: 2026-02-15 (remediation)
- **Next rotation**: 2026-05-15

### Files to Never Commit

The following should ALWAYS be in `.gitignore`:

```
# Environment & Configuration
.env
.env.*
.env.local
.env.*.backup
.env.*.bkp
config.local*

# Credentials
*.pem
*.key
*.ppk
*.p8
secrets/
private/

# CI/CD Secrets
.github/secrets/
gitlab-secrets/

# Database & API Keys
.database.yml
database.yml
```

### Security Checklist

When deploying new instances:

- [ ] Generate fresh API tokens
- [ ] Never reuse old tokens
- [ ] Store tokens in secure vault (e.g., HashiCorp Vault)
- [ ] Enable secret scanning on GitHub
- [ ] Setup token rotation schedule
- [ ] Document token expiration dates
- [ ] Test token revocation process
- [ ] Audit git history before deployment

### Contact & Support

**Security Contact**: oribot@edinprint3d.co.uk

**Response Time**: 48 hours for security reports

---

**Last Updated**: 2026-02-15 22:19 UTC  
**Status**: Remediated ✅  
**Review Schedule**: Quarterly security audits
