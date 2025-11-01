# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of MCP Proxmox Server seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via:
- **Email**: [Create a private security advisory](https://github.com/bsahane/mcp-proxmox/security/advisories/new)
- **GitHub Security Advisory**: Use GitHub's private vulnerability reporting feature

### What to Include

Please include the following information in your report:

1. **Description** of the vulnerability
2. **Steps to reproduce** the issue
3. **Potential impact** of the vulnerability
4. **Suggested fix** (if you have one)
5. **Your contact information** for follow-up

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - **Critical**: 1-7 days
  - **High**: 7-14 days
  - **Medium**: 14-30 days
  - **Low**: 30-90 days

### Disclosure Policy

- We will acknowledge receipt of your vulnerability report
- We will confirm the vulnerability and determine its impact
- We will release a fix as soon as possible
- We will publicly disclose the vulnerability after a fix is available
- We will credit you for the discovery (unless you prefer to remain anonymous)

## Security Best Practices

### For Users

#### 1. API Token Security

- **Use API tokens** instead of username/password authentication
- **Grant minimum required permissions** to API tokens
- **Rotate tokens regularly** (every 90 days recommended)
- **Never commit tokens** to version control
- **Use separate tokens** for different environments (dev/staging/prod)

#### 2. Network Security

- **Enable SSL/TLS verification** in production (`PROXMOX_VERIFY="true"`)
- **Use HTTPS** for all Proxmox API connections
- **Restrict API access** by IP address when possible
- **Use VPN or private networks** for sensitive environments
- **Configure firewall rules** appropriately

#### 3. Environment Configuration

- **Protect `.env` file** with appropriate file permissions (600)
- **Never commit `.env`** to version control
- **Use environment-specific** `.env` files
- **Validate environment variables** before use
- **Audit `.env` file access** regularly

#### 4. Secret Management

- **Never store secrets in VM/LXC notes** - Use the `proxmox-secret-store` tool instead
- **Use encrypted storage** for sensitive data
- **Implement secret rotation** policies
- **Use secret management tools** (HashiCorp Vault, AWS Secrets Manager, etc.)

#### 5. Access Control

- **Implement least privilege** principle
- **Use role-based access control** (RBAC)
- **Audit user permissions** regularly
- **Review API token permissions** periodically
- **Disable unused accounts** and tokens

#### 6. Monitoring and Logging

- **Enable audit logging** for all operations
- **Monitor for suspicious activity**
- **Set up alerts** for security events
- **Review logs regularly**
- **Retain logs** for compliance requirements

### For Developers

#### 1. Code Security

- **Validate all inputs** before processing
- **Sanitize user-provided data**
- **Use parameterized queries** for database operations
- **Avoid eval()** and similar dangerous functions
- **Handle errors securely** (don't expose sensitive information)

#### 2. Dependency Management

- **Keep dependencies up to date**
- **Review security advisories** for dependencies
- **Use `pip-audit`** to scan for vulnerabilities
- **Pin dependency versions** in production
- **Use virtual environments** for isolation

#### 3. Authentication and Authorization

- **Verify API tokens** on every request
- **Implement rate limiting** to prevent abuse
- **Use HTTPS** for all API communications
- **Validate SSL certificates**
- **Implement timeout mechanisms**

#### 4. Data Protection

- **Encrypt sensitive data** at rest and in transit
- **Use secure random number generation**
- **Implement proper key management**
- **Avoid logging sensitive information**
- **Securely delete temporary files**

#### 5. Testing

- **Write security tests**
- **Perform security code reviews**
- **Use static analysis tools** (bandit, safety)
- **Conduct penetration testing**
- **Test error handling** and edge cases

## Known Security Considerations

### 1. API Token Exposure

**Risk**: API tokens in environment variables could be exposed through process listings

**Mitigation**:
- Use file-based token storage with restricted permissions
- Implement token encryption at rest
- Use secret management services

### 2. SSL Certificate Verification

**Risk**: Disabling SSL verification (`PROXMOX_VERIFY="false"`) exposes to MITM attacks

**Mitigation**:
- Only disable in development/testing environments
- Use proper SSL certificates in production
- Implement certificate pinning for critical environments

### 3. Command Injection

**Risk**: User-provided input could be executed as shell commands

**Mitigation**:
- All user inputs are validated and sanitized
- No direct shell command execution with user input
- Use parameterized API calls

### 4. Privilege Escalation

**Risk**: API tokens with excessive permissions

**Mitigation**:
- Document minimum required permissions
- Provide role templates for common use cases
- Audit token permissions regularly

## Security Tools and Resources

### Recommended Tools

- **pip-audit**: Scan Python dependencies for vulnerabilities
- **bandit**: Security linter for Python code
- **safety**: Check dependencies against security database
- **trivy**: Vulnerability scanner for containers and dependencies

### Running Security Scans

```bash
# Install security tools
pip install pip-audit bandit safety

# Scan dependencies
pip-audit

# Scan code for security issues
bandit -r src/

# Check for known vulnerabilities
safety check
```

### GitHub Security Features

- **Dependabot**: Automated dependency updates
- **Code Scanning**: Automated security analysis
- **Secret Scanning**: Detect committed secrets
- **Security Advisories**: Private vulnerability reporting

## Compliance

### Data Protection

- **GDPR**: Ensure proper handling of personal data
- **HIPAA**: Implement appropriate safeguards for healthcare data
- **PCI DSS**: Follow requirements for payment card data

### Audit Requirements

- **Logging**: Maintain audit logs for all operations
- **Access Control**: Document and enforce access policies
- **Encryption**: Use appropriate encryption standards
- **Incident Response**: Have a documented response plan

## Security Updates

We regularly update this document and our security practices. Check back periodically for updates.

**Last Updated**: November 2024  
**Version**: 1.0.0

## Contact

For security concerns or questions:
- **Security Advisory**: [GitHub Security Advisories](https://github.com/bsahane/mcp-proxmox/security/advisories)
- **General Questions**: [GitHub Issues](https://github.com/bsahane/mcp-proxmox/issues) (for non-security issues)

---

Thank you for helping keep MCP Proxmox Server and its users safe!

