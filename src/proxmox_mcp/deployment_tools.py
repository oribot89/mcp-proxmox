"""
Deployment tools for Proxmox LXC containers.
Provides high-level abstractions for service deployment, nginx configuration, and container bootstrapping.
Designed to reduce deployment time from 2.5 hours to <30 minutes for Edinburgh Print 3D and similar projects.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from .container_ops import ContainerOperations


class DeploymentTools:
    """High-level deployment automation for Proxmox containers"""
    
    # Systemd service template
    SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description={app_name} service
After=network.target
Documentation=https://instanceone.cloud

[Service]
Type=notify
User={systemd_user}
WorkingDirectory=/opt/{app_name}
ExecStart=/opt/{app_name}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port {port}
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    # Nginx upstream template
    NGINX_UPSTREAM_TEMPLATE = """upstream {upstream_name}_backend {{
    server 10.0.0.{upstream_ip}:{port};
}}

server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};
    
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    
    # Proxy configuration
    location / {{
        proxy_pass http://{upstream_name}_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }}
}}
"""

    def __init__(
        self,
        proxmox_host: str,
        ssh_key: Optional[str] = None,
        ssh_user: str = "root",
        proxy_gateway_ctid: int = 100
    ):
        """
        Initialize deployment tools.
        
        Args:
            proxmox_host: Proxmox host IP or hostname
            ssh_key: Path to SSH key (default: auto-detect)
            ssh_user: SSH user (default: root)
            proxy_gateway_ctid: Container ID running nginx proxy (default: 100)
        """
        self.container_ops = ContainerOperations(proxmox_host, ssh_key, ssh_user)
        self.proxmox_host = proxmox_host
        self.proxy_gateway_ctid = proxy_gateway_ctid
        self.startup_wait = 3  # Seconds to wait for service startup

    def container_bootstrap(
        self,
        ctid: int,
        packages: List[str] = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Bootstrap a container with common packages.
        
        Idempotent operation - safe to run multiple times.
        
        Args:
            ctid: Container ID
            packages: List of packages to install (default: basic set)
            timeout: Operation timeout in seconds
        
        Returns:
            Dict with keys:
                - success: bool
                - packages_installed: List[str]
                - missing_packages: List[str] (packages that failed to install)
                - installation_time_ms: float
                - message: str
        """
        if packages is None:
            packages = [
                "git",
                "python3-venv",
                "python3-pip",
                "curl",
                "wget",
                "build-essential"
            ]
        
        start_time = time.time()
        
        try:
            # Update package list
            update_result = self.container_ops.exec_in_container(
                ctid,
                "apt-get update",
                timeout=timeout
            )
            
            if not update_result['success']:
                return {
                    "success": False,
                    "packages_installed": [],
                    "missing_packages": packages,
                    "installation_time_ms": (time.time() - start_time) * 1000,
                    "message": f"apt-get update failed: {update_result['error']}"
                }
            
            # Install packages
            packages_str = " ".join(packages)
            install_result = self.container_ops.exec_in_container(
                ctid,
                f"apt-get install -y {packages_str}",
                timeout=timeout
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            if install_result['success']:
                return {
                    "success": True,
                    "packages_installed": packages,
                    "missing_packages": [],
                    "installation_time_ms": elapsed_ms,
                    "message": f"Successfully installed {len(packages)} packages in {elapsed_ms:.0f}ms"
                }
            else:
                # Attempt to identify which packages failed
                output = install_result['error'] or install_result['output']
                missing = []
                for pkg in packages:
                    if f"Unable to locate package {pkg}" in output or f"{pkg} : unable to locate package" in output:
                        missing.append(pkg)
                
                return {
                    "success": False,
                    "packages_installed": [p for p in packages if p not in missing],
                    "missing_packages": missing,
                    "installation_time_ms": elapsed_ms,
                    "message": f"Installation completed with errors. Missing packages: {missing}"
                }
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "packages_installed": [],
                "missing_packages": packages,
                "installation_time_ms": elapsed_ms,
                "message": f"Exception during bootstrap: {str(e)}"
            }

    def pct_deploy_service(
        self,
        ctid: int,
        repo_url: str,
        port: int,
        app_name: str,
        systemd_user: str = "root",
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Deploy a FastAPI/Python service to a container in one call.
        
        Handles: git clone, venv setup, pip install, systemd service creation and startup.
        
        Args:
            ctid: Container ID
            repo_url: Git repository URL
            port: Port to listen on
            app_name: Application name (used for service name and directory)
            systemd_user: User to run service as (default: root)
            timeout: Operation timeout in seconds
        
        Returns:
            Dict with keys:
                - success: bool
                - app_name: str
                - port: int
                - service_status: str
                - pid: int or None
                - uptime_seconds: int or None
                - logs_excerpt: str
                - deployment_time_ms: float
                - message: str
        """
        start_time = time.time()
        app_path = f"/opt/{app_name}"
        service_name = app_name
        
        try:
            # Step 1: Bootstrap with required packages
            bootstrap = self.container_bootstrap(
                ctid,
                packages=["git", "python3-venv", "python3-pip", "build-essential"],
                timeout=120
            )
            
            if not bootstrap['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "app_name": app_name,
                    "port": port,
                    "service_status": "error",
                    "pid": None,
                    "uptime_seconds": None,
                    "logs_excerpt": bootstrap['message'],
                    "deployment_time_ms": elapsed_ms,
                    "message": f"Bootstrap failed: {bootstrap['message']}"
                }
            
            # Step 2: Remove existing directory if it exists
            self.container_ops.exec_in_container(
                ctid,
                f"rm -rf {app_path}",
                timeout=30
            )
            
            # Step 3: Clone repository
            clone_result = self.container_ops.exec_in_container(
                ctid,
                f"git clone {repo_url} {app_path}",
                timeout=120
            )
            
            if not clone_result['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "app_name": app_name,
                    "port": port,
                    "service_status": "error",
                    "pid": None,
                    "uptime_seconds": None,
                    "logs_excerpt": clone_result['error'],
                    "deployment_time_ms": elapsed_ms,
                    "message": f"Git clone failed: {clone_result['error']}"
                }
            
            # Step 4: Create virtual environment
            venv_result = self.container_ops.exec_in_container(
                ctid,
                f"python3 -m venv {app_path}/venv",
                timeout=60
            )
            
            if not venv_result['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "app_name": app_name,
                    "port": port,
                    "service_status": "error",
                    "pid": None,
                    "uptime_seconds": None,
                    "logs_excerpt": venv_result['error'],
                    "deployment_time_ms": elapsed_ms,
                    "message": f"Venv creation failed: {venv_result['error']}"
                }
            
            # Step 5: Install dependencies
            pip_result = self.container_ops.exec_in_container(
                ctid,
                f"{app_path}/venv/bin/pip install -q --upgrade pip setuptools wheel && {app_path}/venv/bin/pip install -q -r {app_path}/requirements.txt",
                timeout=timeout
            )
            
            if not pip_result['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "app_name": app_name,
                    "port": port,
                    "service_status": "error",
                    "pid": None,
                    "uptime_seconds": None,
                    "logs_excerpt": pip_result['error'],
                    "deployment_time_ms": elapsed_ms,
                    "message": f"Pip install failed: {pip_result['error']}"
                }
            
            # Step 6: Create systemd service file
            service_content = self.SYSTEMD_SERVICE_TEMPLATE.format(
                app_name=app_name,
                port=port,
                systemd_user=systemd_user
            )
            
            # Write service file
            service_file_path = f"/etc/systemd/system/{service_name}.service"
            
            # Use base64 encoding for reliability
            import base64
            b64_content = base64.b64encode(service_content.encode('utf-8')).decode('utf-8')
            
            write_service = self.container_ops.exec_in_container(
                ctid,
                f"echo '{b64_content}' | base64 -d > {service_file_path}",
                timeout=10
            )
            
            if not write_service['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "app_name": app_name,
                    "port": port,
                    "service_status": "error",
                    "pid": None,
                    "uptime_seconds": None,
                    "logs_excerpt": write_service['error'],
                    "deployment_time_ms": elapsed_ms,
                    "message": f"Service file creation failed: {write_service['error']}"
                }
            
            # Step 7: Enable and start service
            reload_result = self.container_ops.exec_in_container(
                ctid,
                "systemctl daemon-reload",
                timeout=10
            )
            
            if not reload_result['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "app_name": app_name,
                    "port": port,
                    "service_status": "error",
                    "pid": None,
                    "uptime_seconds": None,
                    "logs_excerpt": reload_result['error'],
                    "deployment_time_ms": elapsed_ms,
                    "message": f"Systemd reload failed: {reload_result['error']}"
                }
            
            # Enable service
            enable_result = self.container_ops.exec_in_container(
                ctid,
                f"systemctl enable {service_name}",
                timeout=10
            )
            
            # Start service
            start_result = self.container_ops.exec_in_container(
                ctid,
                f"systemctl start {service_name}",
                timeout=10
            )
            
            if not start_result['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "app_name": app_name,
                    "port": port,
                    "service_status": "failed",
                    "pid": None,
                    "uptime_seconds": None,
                    "logs_excerpt": start_result['error'],
                    "deployment_time_ms": elapsed_ms,
                    "message": f"Service start failed: {start_result['error']}"
                }
            
            # Wait for service to stabilize
            time.sleep(self.startup_wait)
            
            # Step 8: Verify service status
            status_result = self.container_ops.exec_in_container(
                ctid,
                f"systemctl status {service_name}",
                timeout=10
            )
            
            # Get logs
            logs_result = self.container_ops.exec_in_container(
                ctid,
                f"journalctl -u {service_name} -n 10 --no-pager",
                timeout=10
            )
            
            # Try to get PID
            pid_result = self.container_ops.exec_in_container(
                ctid,
                f"systemctl show {service_name} -p MainPID --value",
                timeout=10
            )
            
            pid = None
            uptime_seconds = None
            if pid_result['success'] and pid_result['output']:
                try:
                    pid = int(pid_result['output'].strip())
                    
                    # Get uptime
                    uptime_result = self.container_ops.exec_in_container(
                        ctid,
                        f"ps -o etimes= -p {pid} 2>/dev/null || echo 0",
                        timeout=10
                    )
                    if uptime_result['success'] and uptime_result['output']:
                        uptime_seconds = int(uptime_result['output'].strip())
                except (ValueError, IndexError):
                    pass
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "app_name": app_name,
                "port": port,
                "service_status": "active",
                "pid": pid,
                "uptime_seconds": uptime_seconds,
                "logs_excerpt": logs_result['output'] if logs_result['success'] else "",
                "deployment_time_ms": elapsed_ms,
                "message": f"Service deployed successfully in {elapsed_ms:.0f}ms"
            }
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "app_name": app_name,
                "port": port,
                "service_status": "error",
                "pid": None,
                "uptime_seconds": None,
                "logs_excerpt": str(e),
                "deployment_time_ms": elapsed_ms,
                "message": f"Unexpected error: {str(e)}"
            }

    def nginx_add_upstream(
        self,
        domain: str,
        ctid: int,
        port: int,
        cert_provider: str = "letsencrypt",
        email: str = "admin@instanceone.co",
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Configure nginx upstream and SSL certificate for a new domain.
        
        Handles: certbot setup, nginx config creation, config validation, and reload.
        
        Args:
            domain: Domain name (e.g., "beta.edinprint3d.co.uk")
            ctid: Container ID running the service
            port: Service port inside container
            cert_provider: Certificate provider (default: "letsencrypt")
            email: Email for Let's Encrypt (default: admin@instanceone.co)
            timeout: Operation timeout in seconds
        
        Returns:
            Dict with keys:
                - success: bool
                - domain: str
                - upstream_ip: str (10.0.0.{ctid})
                - upstream_port: int
                - cert_path: str
                - cert_expiry: str (or None if error)
                - nginx_status: str
                - configuration_time_ms: float
                - message: str
        """
        start_time = time.time()
        upstream_ip = ctid
        upstream_name = domain.replace(".", "_").replace("-", "_")
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        sites_available = f"/etc/nginx/sites-available/{upstream_name}"
        sites_enabled = f"/etc/nginx/sites-enabled/{upstream_name}"
        
        try:
            # Step 1: Check if domain already has a configuration
            check_config = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                f"test -f {sites_available} && echo EXISTS || echo NOTFOUND",
                timeout=10
            )
            
            if check_config['success'] and "EXISTS" in check_config['output']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "domain": domain,
                    "upstream_ip": f"10.0.0.{ctid}",
                    "upstream_port": port,
                    "cert_path": cert_path,
                    "cert_expiry": None,
                    "nginx_status": "already_exists",
                    "configuration_time_ms": elapsed_ms,
                    "message": f"Nginx configuration for {domain} already exists"
                }
            
            # Step 2: Check if certificate exists, create if not
            cert_check = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                f"test -f {cert_path} && echo EXISTS || echo NOTFOUND",
                timeout=10
            )
            
            if cert_check['success'] and "NOTFOUND" in cert_check['output']:
                # Certificate doesn't exist, create it
                certbot_result = self.container_ops.exec_in_container(
                    self.proxy_gateway_ctid,
                    f"certbot certonly --standalone -d {domain} --non-interactive --agree-tos -m {email} --preferred-challenges http",
                    timeout=timeout
                )
                
                if not certbot_result['success']:
                    elapsed_ms = (time.time() - start_time) * 1000
                    return {
                        "success": False,
                        "domain": domain,
                        "upstream_ip": f"10.0.0.{ctid}",
                        "upstream_port": port,
                        "cert_path": cert_path,
                        "cert_expiry": None,
                        "nginx_status": "cert_generation_failed",
                        "configuration_time_ms": elapsed_ms,
                        "message": f"Certificate generation failed: {certbot_result['error']}"
                    }
            
            # Step 3: Verify certificate exists
            verify_cert = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                f"test -f {cert_path} && test -f {key_path} && echo OK || echo MISSING",
                timeout=10
            )
            
            if not verify_cert['success'] or "MISSING" in verify_cert['output']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "domain": domain,
                    "upstream_ip": f"10.0.0.{ctid}",
                    "upstream_port": port,
                    "cert_path": cert_path,
                    "cert_expiry": None,
                    "nginx_status": "cert_missing",
                    "configuration_time_ms": elapsed_ms,
                    "message": f"Certificate not found at {cert_path} or key not found at {key_path}"
                }
            
            # Step 4: Generate nginx configuration
            nginx_config = self.NGINX_UPSTREAM_TEMPLATE.format(
                upstream_name=upstream_name,
                upstream_ip=upstream_ip,
                port=port,
                domain=domain
            )
            
            # Write nginx config using base64 encoding
            import base64
            b64_config = base64.b64encode(nginx_config.encode('utf-8')).decode('utf-8')
            
            write_config = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                f"echo '{b64_config}' | base64 -d > {sites_available}",
                timeout=10
            )
            
            if not write_config['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "domain": domain,
                    "upstream_ip": f"10.0.0.{ctid}",
                    "upstream_port": port,
                    "cert_path": cert_path,
                    "cert_expiry": None,
                    "nginx_status": "config_write_failed",
                    "configuration_time_ms": elapsed_ms,
                    "message": f"Failed to write nginx config: {write_config['error']}"
                }
            
            # Step 5: Create symlink in sites-enabled
            symlink_result = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                f"ln -sf {sites_available} {sites_enabled}",
                timeout=10
            )
            
            # Step 6: Validate nginx configuration
            test_result = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                "nginx -t",
                timeout=10
            )
            
            if not test_result['success']:
                # Rollback: remove the config
                self.container_ops.exec_in_container(
                    self.proxy_gateway_ctid,
                    f"rm -f {sites_available} {sites_enabled}",
                    timeout=10
                )
                
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "domain": domain,
                    "upstream_ip": f"10.0.0.{ctid}",
                    "upstream_port": port,
                    "cert_path": cert_path,
                    "cert_expiry": None,
                    "nginx_status": "config_validation_failed",
                    "configuration_time_ms": elapsed_ms,
                    "message": f"Nginx configuration validation failed: {test_result['error']}"
                }
            
            # Step 7: Reload nginx
            reload_result = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                "systemctl reload nginx",
                timeout=10
            )
            
            if not reload_result['success']:
                elapsed_ms = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "domain": domain,
                    "upstream_ip": f"10.0.0.{ctid}",
                    "upstream_port": port,
                    "cert_path": cert_path,
                    "cert_expiry": None,
                    "nginx_status": "reload_failed",
                    "configuration_time_ms": elapsed_ms,
                    "message": f"Nginx reload failed: {reload_result['error']}"
                }
            
            # Step 8: Get certificate expiry information
            cert_expiry = None
            expiry_result = self.container_ops.exec_in_container(
                self.proxy_gateway_ctid,
                f"openssl x509 -enddate -noout -in {cert_path}",
                timeout=10
            )
            
            if expiry_result['success']:
                cert_expiry = expiry_result['output'].strip()
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "domain": domain,
                "upstream_ip": f"10.0.0.{ctid}",
                "upstream_port": port,
                "cert_path": cert_path,
                "cert_expiry": cert_expiry,
                "nginx_status": "active",
                "configuration_time_ms": elapsed_ms,
                "message": f"Nginx upstream configured and reloaded in {elapsed_ms:.0f}ms"
            }
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "domain": domain,
                "upstream_ip": f"10.0.0.{ctid}",
                "upstream_port": port,
                "cert_path": cert_path,
                "cert_expiry": None,
                "nginx_status": "error",
                "configuration_time_ms": elapsed_ms,
                "message": f"Unexpected error: {str(e)}"
            }
