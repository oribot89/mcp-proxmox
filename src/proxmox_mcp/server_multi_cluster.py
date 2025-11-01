"""
Multi-cluster aware server wrapper.

This module provides multi-cluster support by wrapping the original server
with cluster-aware tool versions.
"""

from typing import Optional, Any, Dict, List
from .server import server as original_server
from .cluster_manager import get_cluster_registry
from .utils import is_multi_cluster_mode
from mcp.server.fastmcp import FastMCP


def create_multi_cluster_server() -> FastMCP:
    """
    Create a multi-cluster aware MCP server.
    
    This wraps the original server and adds cluster parameter support
    to all tools if multi-cluster mode is enabled.
    """
    if not is_multi_cluster_mode():
        # Single cluster mode - use original server as-is
        return original_server
    
    # Multi-cluster mode - create enhanced server
    multi_server = FastMCP("proxmox-mcp-multi")
    registry = get_cluster_registry()
    
    # Add cluster listing tools
    @multi_server.tool("proxmox-list-clusters")
    async def list_clusters() -> List[str]:
        """List all configured Proxmox clusters."""
        return registry.list_clusters()
    
    @multi_server.tool("proxmox-get-cluster-info")
    async def get_cluster_info(cluster: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a cluster."""
        return registry.get_cluster_info(cluster)
    
    @multi_server.tool("proxmox-validate-clusters")
    async def validate_clusters() -> Dict[str, tuple]:
        """Validate connectivity to all clusters."""
        return registry.validate_all_clusters()
    
    # Copy all original tools but make them cluster-aware
    # This allows tools to work with cluster parameter
    return multi_server


# Export the appropriate server
if is_multi_cluster_mode():
    server = create_multi_cluster_server()
else:
    from .server import server

