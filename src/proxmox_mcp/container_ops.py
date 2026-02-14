"""
Container operations for Proxmox LXC containers.
Provides tools for executing commands, managing files, and monitoring containers.
"""

from __future__ import annotations

import base64
import os
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from .utils import require_confirm


class ContainerOperations:
    """High-level container operations using SSH + pct commands"""
    
    def __init__(self, proxmox_host: str, ssh_key: Optional[str] = None, ssh_user: str = "root"):
        """
        Initialize container operations.
        
        Args:
            proxmox_host: Proxmox host IP or hostname
            ssh_key: Path to SSH key (default: ~/.ssh/id_openssh or id_rsa)
            ssh_user: SSH user (default: root)
        """
        self.proxmox_host = proxmox_host
        self.ssh_user = ssh_user
        
        # Find SSH key
        if ssh_key:
            self.ssh_key = ssh_key
        else:
            # Try common locations
            for key_path in [
                "~/.ssh/id_openclaw",
                "~/.ssh/id_openssh", 
                "~/.ssh/id_rsa",
                "~/.ssh/id_ed25519"
            ]:
                expanded = os.path.expanduser(key_path)
                if os.path.exists(expanded):
                    self.ssh_key = expanded
                    break
            else:
                raise ValueError("Could not find SSH key. Provide ssh_key parameter.")
        
        self.timeout = 30  # Default timeout for SSH commands
    
    def _run_ssh_command(self, command: str, timeout: int = None) -> Tuple[int, str, str]:
        """
        Execute command on Proxmox host via SSH.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if timeout is None:
            timeout = self.timeout
        
        full_cmd = [
            "ssh",
            "-i", self.ssh_key,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            f"{self.ssh_user}@{self.proxmox_host}",
            command
        ]
        
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return 1, "", str(e)
    
    def exec_in_container(
        self, 
        vmid: int, 
        command: str,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Execute command inside LXC container.
        
        Args:
            vmid: Container ID
            command: Command to execute
            timeout: Command timeout in seconds (default: 30)
        
        Returns:
            Dict with keys:
                - success: bool
                - output: str (stdout)
                - error: str (stderr)
                - exit_code: int
        """
        # Escape command for pct exec
        escaped_cmd = f'pct exec {vmid} -- {command}'
        
        exit_code, stdout, stderr = self._run_ssh_command(escaped_cmd, timeout)
        
        return {
            "success": exit_code == 0,
            "output": stdout.strip(),
            "error": stderr.strip() if stderr else None,
            "exit_code": exit_code
        }
    
    def push_file_to_container(
        self,
        vmid: int,
        local_path: str,
        remote_path: str
    ) -> Dict[str, Any]:
        """
        Copy file from host into container using base64 encoding.
        
        Args:
            vmid: Container ID
            local_path: Local file path
            remote_path: Destination path in container
        
        Returns:
            Dict with keys:
                - success: bool
                - message: str
                - file_size: int (bytes)
        """
        try:
            # Read local file
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            file_size = len(file_data)
            
            # Base64 encode
            b64_data = base64.b64encode(file_data).decode('utf-8')
            
            # Create directory if needed
            remote_dir = remote_path.rsplit('/', 1)[0]
            self.exec_in_container(vmid, f"mkdir -p {remote_dir}")
            
            # Decode in container using base64
            # Split into chunks to avoid shell line length limits
            chunk_size = 500  # Characters per chunk
            chunks = [b64_data[i:i+chunk_size] for i in range(0, len(b64_data), chunk_size)]
            
            # Build command to write file
            decode_cmd = f"echo '{chunks[0]}' | base64 -d > {remote_path}"
            for chunk in chunks[1:]:
                decode_cmd += f" && echo '{chunk}' | base64 -d >> {remote_path}"
            
            result = self.exec_in_container(vmid, decode_cmd)
            
            if result['success']:
                return {
                    "success": True,
                    "message": f"File pushed successfully to {remote_path}",
                    "file_size": file_size
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to push file: {result['error']}",
                    "file_size": 0
                }
        
        except FileNotFoundError:
            return {
                "success": False,
                "message": f"Local file not found: {local_path}",
                "file_size": 0
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error pushing file: {str(e)}",
                "file_size": 0
            }
    
    def pull_file_from_container(
        self,
        vmid: int,
        remote_path: str,
        local_path: str
    ) -> Dict[str, Any]:
        """
        Copy file from container to host using base64 encoding.
        
        Args:
            vmid: Container ID
            remote_path: File path in container
            local_path: Destination on host
        
        Returns:
            Dict with keys:
                - success: bool
                - message: str
                - file_size: int (bytes)
        """
        try:
            # Check if file exists in container
            check_result = self.exec_in_container(vmid, f"test -f {remote_path} && echo OK")
            if not check_result['success']:
                return {
                    "success": False,
                    "message": f"File not found in container: {remote_path}",
                    "file_size": 0
                }
            
            # Base64 encode in container and retrieve
            encode_result = self.exec_in_container(vmid, f"base64 -w0 {remote_path}")
            if not encode_result['success']:
                return {
                    "success": False,
                    "message": f"Failed to read file: {encode_result['error']}",
                    "file_size": 0
                }
            
            # Decode on host
            b64_data = encode_result['output']
            file_data = base64.b64decode(b64_data)
            
            # Write to local path
            os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            return {
                "success": True,
                "message": f"File pulled successfully to {local_path}",
                "file_size": len(file_data)
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Error pulling file: {str(e)}",
                "file_size": 0
            }
    
    def check_container_network(
        self,
        vmid: int,
        test_ip: str = "10.0.0.1",
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Check if container network is operational via ping.
        
        Args:
            vmid: Container ID
            test_ip: IP to ping (default: gateway at 10.0.0.1)
            timeout: Ping timeout in seconds
        
        Returns:
            Dict with keys:
                - online: bool (True if responsive)
                - latency_ms: float (round-trip time in milliseconds, or None)
                - error: str (error message if failed)
        """
        ping_cmd = f"ping -c 1 -W {timeout} {test_ip}"
        result = self.exec_in_container(vmid, ping_cmd, timeout=timeout + 5)
        
        if result['success']:
            # Parse latency from ping output
            output = result['output']
            try:
                # Look for "time=X.XX ms" in output
                for line in output.split('\n'):
                    if 'time=' in line:
                        time_part = line.split('time=')[1].split(' ')[0]
                        latency = float(time_part)
                        return {
                            "online": True,
                            "latency_ms": latency,
                            "error": None
                        }
            except (IndexError, ValueError):
                pass
            
            # If we can't parse, but ping succeeded
            return {
                "online": True,
                "latency_ms": None,
                "error": None
            }
        else:
            return {
                "online": False,
                "latency_ms": None,
                "error": result['error'] or "Network unreachable"
            }
    
    def get_container_config(
        self,
        vmid: int,
        key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get container configuration.
        
        Args:
            vmid: Container ID
            key: Optional specific key to retrieve
        
        Returns:
            Dict with container configuration
        """
        result = self.exec_in_container(vmid, "cat /etc/hostname")
        hostname = result['output'] if result['success'] else "unknown"
        
        # Get network info
        net_result = self.exec_in_container(vmid, "ip addr show")
        
        # Get resource info
        res_result = self.exec_in_container(vmid, "free -h && df -h /")
        
        config = {
            "vmid": vmid,
            "hostname": hostname.strip(),
            "network": net_result['output'] if net_result['success'] else None,
            "resources": res_result['output'] if res_result['success'] else None
        }
        
        if key:
            return config.get(key)
        
        return config
    
    def wait_for_container_network(
        self,
        vmid: int,
        max_retries: int = 30,
        retry_delay: int = 5,
        test_ip: str = "10.0.0.1"
    ) -> Dict[str, Any]:
        """
        Wait for container network to come online.
        
        Args:
            vmid: Container ID
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            test_ip: IP to test
        
        Returns:
            Dict with keys:
                - online: bool
                - attempts: int
                - total_wait_ms: float
                - error: str (if failed)
        """
        import time
        start_time = time.time()
        
        for attempt in range(max_retries):
            net_check = self.check_container_network(vmid, test_ip)
            
            if net_check['online']:
                elapsed = (time.time() - start_time) * 1000
                return {
                    "online": True,
                    "attempts": attempt + 1,
                    "total_wait_ms": elapsed,
                    "error": None
                }
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        elapsed = (time.time() - start_time) * 1000
        return {
            "online": False,
            "attempts": max_retries,
            "total_wait_ms": elapsed,
            "error": f"Network did not come online after {max_retries} retries"
        }
