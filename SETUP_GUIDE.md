# Proxmox MCP Setup Guide for OpenClaw

This is a fork of [bsahane/mcp-proxmox](https://github.com/bsahane/mcp-proxmox) configured for integration with OpenClaw and Proxmox VE 9.1.5 at `5.135.136.29`.

## Prerequisites

1. **Proxmox VE** running at `https://5.135.136.29:8006`
2. **Python 3.10+** installed
3. **API Token** created in Proxmox with appropriate permissions

## Step 1: Create Proxmox API Token

1. Log into Proxmox Web UI: `https://5.135.136.29:8006`
2. Navigate to **Datacenter > Permissions > API Tokens**
3. Click **"Add"** to create new token
4. Fill in:
   - **User**: `root@pam`
   - **Token ID**: `mcp-proxmox`
   - **Privilege Separation**: Uncheck (for full access) or check for specific roles
5. Click **Add**
6. **Save the token secret** (you won't see it again)

Format: `root@pam!mcp-proxmox` (User + ! + Token ID)

## Step 2: Configure .env

```bash
cd /path/to/proxmox-mcp
cp .env.example .env
```

Edit `.env` with your values:

```bash
PROXMOX_API_URL="https://5.135.136.29:8006"
PROXMOX_TOKEN_ID="root@pam!mcp-proxmox"
PROXMOX_TOKEN_SECRET="<your-token-secret-from-step-1>"
PROXMOX_VERIFY="true"
PROXMOX_DEFAULT_NODE="EXAPVERBX01"
PROXMOX_DEFAULT_STORAGE="local"
PROXMOX_DEFAULT_BRIDGE="vmbr0"
```

⚠️ **Important**: `.env` is in `.gitignore` and will NOT be committed to git.

## Step 3: Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e .  # Optional: install as console script
```

## Step 4: Test Connection

```bash
source .venv/bin/activate
python -m proxmox_mcp.server
```

Or if installed as console script:

```bash
source .venv/bin/activate
proxmox-mcp
```

You should see the MCP server start. Press `Ctrl+C` to stop.

## Step 5: Integrate with OpenClaw (Optional)

Add to your OpenClaw config:

```json
{
  "agents": {
    "defaults": {
      "mcpServers": {
        "proxmox-mcp": {
          "command": "python",
          "args": ["-m", "proxmox_mcp.server"],
          "env": {
            "PROXMOX_API_URL": "https://5.135.136.29:8006",
            "PROXMOX_TOKEN_ID": "root@pam!mcp-proxmox",
            "PROXMOX_TOKEN_SECRET": "YOUR_TOKEN_SECRET",
            "PROXMOX_VERIFY": "true"
          }
        }
      }
    }
  }
}
```

Then reload OpenClaw configuration:

```bash
openclaw gateway restart
```

## Available Tools

The MCP server exposes rich Proxmox utilities:

### Discovery
- `proxmox-list-nodes` - List cluster nodes
- `proxmox-node-status` - Node health & details
- `proxmox-list-vms` - List virtual machines
- `proxmox-vm-info` - Get VM configuration
- `proxmox-list-lxc` - List LXC containers
- `proxmox-lxc-info` - Get LXC configuration
- `proxmox-list-storage` - List storage pools
- `proxmox-list-tasks` - Recent cluster tasks

### Lifecycle (VMs)
- `proxmox-start-vm` - Start a VM
- `proxmox-stop-vm` - Stop a VM
- `proxmox-reboot-vm` - Reboot a VM
- `proxmox-clone-vm` - Clone a VM
- `proxmox-create-vm` - Create new VM
- `proxmox-delete-vm` - Delete a VM
- `proxmox-migrate-vm` - Migrate VM to another node

### Snapshots & Backups
- `proxmox-create-snapshot` - Create VM snapshot
- `proxmox-list-snapshots` - List snapshots
- `proxmox-rollback-snapshot` - Restore from snapshot
- `proxmox-create-backup` - Create VM backup

### Containers
- `proxmox-start-lxc` - Start container
- `proxmox-stop-lxc` - Stop container

### Metrics & Status
- `proxmox-get-node-resources` - CPU/memory/disk stats
- `proxmox-task-status` - Check operation status

See `README.md` for complete tool reference.

## Security Notes

1. **Token Secret**: Never commit `.env` to git
2. **ACL Permissions**: For read-only, use `PVEAuditor`; for write, use `PVEVMAdmin` on specific pools
3. **SSL Verification**: `PROXMOX_VERIFY=true` validates certificates
4. **Token Rotation**: Plan to rotate tokens periodically

## Development & Contributing

This is a fork of `bsahane/mcp-proxmox`. To contribute improvements:

1. Make changes in a feature branch
2. Test thoroughly
3. Submit PR to upstream `bsahane/mcp-proxmox` or keep changes local
4. Update this guide if needed

## Troubleshooting

### "Connection refused"
- Verify Proxmox is running: `ping 5.135.136.29`
- Check firewall allows port 8006
- Verify `PROXMOX_API_URL` in `.env`

### "Invalid token"
- Verify token ID format: `root@pam!mcp-proxmox`
- Check token secret is correct (created in step 1)
- Ensure token is still active (not deleted)

### "Permission denied"
- Check token has correct ACL permissions
- For read-only ops, grant `PVEAuditor` at `/`
- For write ops, grant `PVEVMAdmin` on pool

### "HTTPS certificate verification failed"
- Ensure `PROXMOX_VERIFY="true"` or `false` as needed
- For self-signed certs in dev, use `false` (not recommended for production)

## References

- Upstream: https://github.com/bsahane/mcp-proxmox
- Proxmox API Docs: https://pve.proxmox.com/pve-docs/api-viewer/
- MCP Specification: https://modelcontextprotocol.io/
- OpenClaw Docs: https://docs.openclaw.ai/

---

**Repository**: https://github.com/oribot89/mcp-proxmox  
**Original**: https://github.com/bsahane/mcp-proxmox  
**Status**: Fork for OpenClaw integration (2026-02-14)
