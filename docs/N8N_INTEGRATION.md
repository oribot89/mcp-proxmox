# n8n Integration Guide for MCP Proxmox Server

This guide explains how to integrate the MCP Proxmox Server with n8n (workflow automation tool) using the SSE/HTTP API.

## Quick Start

### 1. Start the Server

```bash
cd /Users/bsahane/Developer/cursor/mcp-proxmox
source .venv/bin/activate
python -m proxmox_mcp.server --transport sse --host 0.0.0.0 --port 8000
```

The server will be available at: `http://0.0.0.0:8000`

### 2. Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server information and available endpoints |
| `/health` | GET | Health check and Proxmox connectivity status |
| `/tools` | GET | List all 118 available MCP tools |
| `/execute` | POST | Execute an MCP tool |
| `/stream` | GET | SSE streaming endpoint (real-time updates) |
| `/docs` | GET | Interactive API documentation (Swagger UI) |

### 3. Using with n8n

#### HTTP Request Node Configuration

**List All Tools:**
```
Method: GET
URL: http://localhost:8000/tools
```

**Execute a Tool:**
```
Method: POST
URL: http://localhost:8000/execute?tool=proxmox-list-all-clusters
Headers:
  Content-Type: application/json
Body (JSON):
  {}
```

**Execute Tool with Parameters:**
```
Method: POST
URL: http://localhost:8000/execute?tool=proxmox-list-vms
Headers:
  Content-Type: application/json
Body (JSON):
  {
    "node": "pve",
    "cluster": "production"
  }
```

## Example n8n Workflows

### Workflow 1: List All VMs from All Clusters

1. **HTTP Request Node**
   - Method: `POST`
   - URL: `http://localhost:8000/execute?tool=proxmox-list-all-vms-from-all-clusters`
   - Body: `{}`

2. **Process Response**
   - The response will contain VMs grouped by cluster
   - Use n8n's data transformation nodes to process results

### Workflow 2: Create VM

1. **HTTP Request Node**
   - Method: `POST`
   - URL: `http://localhost:8000/execute?tool=proxmox-create-vm`
   - Body:
     ```json
     {
       "node": "pve",
       "vmid": 100,
       "name": "test-vm",
       "memory": 2048,
       "cores": 2,
       "disk_size": "32G"
     }
     ```

### Workflow 3: Monitor Cluster Health

1. **Schedule Trigger** (every 5 minutes)
2. **HTTP Request Node**
   - Method: `POST`
   - URL: `http://localhost:8000/execute?tool=proxmox-get-all-cluster-status`
   - Body: `{}`
3. **IF Node** - Check if any cluster is unhealthy
4. **Send Alert** (Email/Slack/etc.)

## Remote Access via Cloudflare Tunnel

If you're using Cloudflare Tunnel (like `n9n.sahane.in`), configure it to route requests:

```yaml
# cloudflared config.yml
tunnel: your-tunnel-id
credentials-file: /path/to/credentials.json

ingress:
  - hostname: n9n.sahane.in
    service: http://localhost:3000  # n8n
  - hostname: proxmox-api.sahane.in
    service: http://localhost:8000  # MCP Proxmox Server
  - service: http_status:404
```

Then access from n8n:
```
URL: https://proxmox-api.sahane.in/execute?tool=proxmox-list-nodes
```

## Available Tools (118 Total)

### Cluster Management
- `proxmox-list-all-clusters` - List all configured clusters
- `proxmox-list-all-nodes-from-all-clusters` - List nodes from all clusters
- `proxmox-get-all-cluster-status` - Get comprehensive cluster status

### VM Management
- `proxmox-list-vms` - List VMs on a node
- `proxmox-create-vm` - Create a new VM
- `proxmox-start-vm` - Start a VM
- `proxmox-stop-vm` - Stop a VM
- `proxmox-delete-vm` - Delete a VM
- `proxmox-clone-vm` - Clone a VM

### Container Management
- `proxmox-list-lxc` - List LXC containers
- `proxmox-create-lxc` - Create a new container
- `proxmox-start-lxc` - Start a container
- `proxmox-stop-lxc` - Stop a container

### Network Management
- `proxmox-list-networks` - List network configurations
- `proxmox-create-vlan` - Create a VLAN
- `proxmox-configure-firewall` - Configure firewall rules

### Storage Management
- `proxmox-list-storage` - List storage configurations
- `proxmox-create-storage` - Add storage
- `proxmox-list-backups` - List backups

### Security & Authentication
- `proxmox-setup-mfa` - Setup multi-factor authentication
- `proxmox-rotate-api-token` - Rotate API tokens
- `proxmox-audit-security` - Run security audit

### Monitoring & Observability
- `proxmox-get-metrics` - Get performance metrics
- `proxmox-export-logs` - Export logs
- `proxmox-setup-prometheus` - Setup Prometheus monitoring

...and 90+ more tools! Use `GET /tools` to see the complete list.

## Response Format

### Success Response
```json
{
  "success": true,
  "tool": "proxmox-list-all-clusters",
  "result": [
    [
      {
        "type": "text",
        "text": "production",
        "annotations": null,
        "_meta": null
      }
    ],
    {
      "result": ["production", "staging"]
    }
  ]
}
```

### Error Response
```json
{
  "success": false,
  "error": "Tool 'invalid-tool' not found",
  "type": "ToolNotFound"
}
```

## Troubleshooting

### Port Already in Use
```bash
# Kill existing server
pkill -f "proxmox_mcp.server"

# Or kill specific port
lsof -ti:8000 | xargs kill -9
```

### Server Not Starting
```bash
# Check logs
tail -f /tmp/mcp-server.log

# Verify dependencies
pip install -r requirements.txt
```

### Connection Refused
- Ensure server is running: `curl http://localhost:8000/health`
- Check firewall rules
- Verify host/port configuration

## Security Considerations

1. **API Access**: The server has no authentication by default. Use:
   - Reverse proxy with authentication (nginx, Caddy)
   - VPN or SSH tunnel for remote access
   - Cloudflare Access for zero-trust security

2. **Proxmox Credentials**: Stored in `.env` file - keep secure!

3. **Network Exposure**: When using `--host 0.0.0.0`, the server is accessible from network. Consider:
   - Binding to `127.0.0.1` for local-only access
   - Using firewall rules to restrict access
   - Implementing rate limiting

## Performance Tips

1. **Concurrent Requests**: The server handles multiple concurrent requests
2. **Caching**: Tool results are not cached - each request hits Proxmox API
3. **Rate Limiting**: Consider implementing rate limiting in n8n workflows
4. **Connection Pooling**: The server maintains connection pools to Proxmox clusters

## Support

- GitHub Issues: https://github.com/bsahane/mcp-proxmox/issues
- Documentation: https://github.com/bsahane/mcp-proxmox/blob/main/README.md
- API Docs: http://localhost:8000/docs (when server is running)

