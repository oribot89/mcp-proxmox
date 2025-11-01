"""
MCP Proxmox - A Model Context Protocol (MCP) server for Proxmox Virtual Environment
"""

__version__ = "0.2.0"

from .client import ProxmoxClient
from .server import server
from .utils import require_confirm, format_size, ClusterConfig, ClusterRegistryConfig, read_multi_cluster_env, load_cluster_registry_config, is_multi_cluster_mode
from .cloudinit import CloudInitConfig, CloudInitProvisioner
from .rhcos import IgnitionConfig, RHCOSProvisioner, OpenShiftInstaller
from .windows import WindowsConfig, WindowsProvisioner
from .docker_swarm import DockerSwarmConfig, DockerSwarmProvisioner
from .cluster_manager import ClusterRegistry, get_cluster_registry, reset_cluster_registry, ClusterError, ClusterNotFoundError, ClusterConnectionError, AmbiguousClusterSelectionError
from .multi_cluster_client import MultiClusterProxmoxClient

__all__ = [
    "__version__",
    "ProxmoxClient",
    "server", 
    "require_confirm",
    "format_size",
    "CloudInitConfig",
    "CloudInitProvisioner",
    "IgnitionConfig",
    "RHCOSProvisioner",
    "OpenShiftInstaller",
    "WindowsConfig",
    "WindowsProvisioner",
    "DockerSwarmConfig",
    "DockerSwarmProvisioner",
    # Multi-cluster support
    "ClusterConfig",
    "ClusterRegistryConfig",
    "ClusterRegistry",
    "MultiClusterProxmoxClient",
    "get_cluster_registry",
    "reset_cluster_registry",
    "ClusterError",
    "ClusterNotFoundError",
    "ClusterConnectionError",
    "AmbiguousClusterSelectionError",
    "read_multi_cluster_env",
    "load_cluster_registry_config",
    "is_multi_cluster_mode",
]
