#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import configparser
import getpass
import json
import os
import paramiko
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class ServerManager:
    """Manages server connections and operations."""
    
    def __init__(self, credentials_file: str = 'server_credentials.json'):
        """Initialize the server manager.
        
        Args:
            credentials_file: Path to the credentials file.
        """
        self.credentials_file = credentials_file
        self.credentials: Dict[str, Dict[str, str]] = {}
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.sftp_client: Optional[paramiko.SFTPClient] = None
        self.current_server: Optional[str] = None
        
        # Load credentials if file exists
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load server credentials from file."""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    self.credentials = json.load(f)
                print(f"{Colors.GREEN}Loaded credentials for {len(self.credentials)} servers.{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.FAIL}Error loading credentials: {e}{Colors.ENDC}")
                self.credentials = {}
        else:
            print(f"{Colors.WARNING}No credentials file found. Starting with empty credentials.{Colors.ENDC}")
            self.credentials = {}
    
    def _save_credentials(self) -> None:
        """Save server credentials to file."""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(self.credentials, f, indent=4)
            print(f"{Colors.GREEN}Credentials saved successfully.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}Error saving credentials: {e}{Colors.ENDC}")
    
    def add_server(self, name: str, ip: str, username: str, password: str) -> None:
        """Add a new server to the credentials.
        
        Args:
            name: Server name/alias.
            ip: Server IP address.
            username: SSH username.
            password: SSH password.
        """
        self.credentials[name] = {
            'ip': ip,
            'username': username,
            'password': password
        }
        self._save_credentials()
        print(f"{Colors.GREEN}Server '{name}' added successfully.{Colors.ENDC}")
    
    def remove_server(self, name: str) -> None:
        """Remove a server from the credentials.
        
        Args:
            name: Server name/alias.
        """
        if name in self.credentials:
            del self.credentials[name]
            self._save_credentials()
            print(f"{Colors.GREEN}Server '{name}' removed successfully.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}Server '{name}' not found.{Colors.ENDC}")
    
    def list_servers(self) -> None:
        """List all saved servers."""
        if not self.credentials:
            print(f"{Colors.WARNING}No servers found.{Colors.ENDC}")
            return
        
        print(f"{Colors.HEADER}\nSaved Servers:{Colors.ENDC}")
        print(f"{Colors.BOLD}{'Name':<20} {'IP Address':<20} {'Username':<20}{Colors.ENDC}")
        print("-" * 60)
        
        for name, details in self.credentials.items():
            print(f"{name:<20} {details['ip']:<20} {details['username']:<20}")
        print()
    
    def connect(self, server_name: str) -> bool:
        """Connect to a server.
        
        Args:
            server_name: Name of the server to connect to.
            
        Returns:
            bool: True if connection successful, False otherwise.
        """
        if server_name not in self.credentials:
            print(f"{Colors.FAIL}Server '{server_name}' not found.{Colors.ENDC}")
            return False
        
        server = self.credentials[server_name]
        
        try:
            print(f"{Colors.CYAN}Connecting to {server_name} ({server['ip']})...{Colors.ENDC}")
            
            # Close existing connections if any
            self.disconnect()
            
            # Create new SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=server['ip'],
                username=server['username'],
                password=server['password'],
                timeout=10
            )
            
            # Create SFTP client
            self.sftp_client = self.ssh_client.open_sftp()
            
            self.current_server = server_name
            print(f"{Colors.GREEN}Connected to {server_name}.{Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}Connection failed: {e}{Colors.ENDC}")
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the current server."""
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None
        
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
        
        if self.current_server:
            print(f"{Colors.CYAN}Disconnected from {self.current_server}.{Colors.ENDC}")
            self.current_server = None
    
    def execute_command(self, command: str) -> tuple:
        """Execute a command on the connected server.

        Args:
            command: Command to execute.

        Returns:
            tuple: (stdout, stderr)
        """
        if not self.ssh_client or not self.current_server:
            print(f"{Colors.FAIL}Not connected to any server.{Colors.ENDC}")
            return ('', 'Not connected to any server')
        
        try:
            print(f"{Colors.CYAN}Executing: {command}{Colors.ENDC}")
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            
            if stdout_str:
                print(f"{Colors.GREEN}Output:{Colors.ENDC}\n{stdout_str}")
            
            if stderr_str:
                print(f"{Colors.FAIL}Error:{Colors.ENDC}\n{stderr_str}")
            
            return (stdout_str, stderr_str)
            
        except Exception as e:
            print(f"{Colors.FAIL}Command execution failed: {e}{Colors.ENDC}")
            return ('', str(e))
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to the connected server.
        
        Args:
            local_path: Path to the local file.
            remote_path: Path on the remote server.
            
        Returns:
            bool: True if upload successful, False otherwise.
        """
        if not self.sftp_client or not self.current_server:
            print(f"{Colors.FAIL}Not connected to any server.{Colors.ENDC}")
            return False
        
        try:
            print(f"{Colors.CYAN}Uploading {local_path} to {remote_path}...{Colors.ENDC}")
            self.sftp_client.put(local_path, remote_path)
            print(f"{Colors.GREEN}Upload successful.{Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}Upload failed: {e}{Colors.ENDC}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the connected server.
        
        Args:
            remote_path: Path on the remote server.
            local_path: Path to save the file locally.
            
        Returns:
            bool: True if download successful, False otherwise.
        """
        if not self.sftp_client or not self.current_server:
            print(f"{Colors.FAIL}Not connected to any server.{Colors.ENDC}")
            return False
        
        try:
            print(f"{Colors.CYAN}Downloading {remote_path} to {local_path}...{Colors.ENDC}")
            self.sftp_client.get(remote_path, local_path)
            print(f"{Colors.GREEN}Download successful.{Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}Download failed: {e}{Colors.ENDC}")
            return False


class DeploymentManager:
    """Manages deployment of the Telegram tracker to servers."""
    
    def __init__(self, server_manager: ServerManager):
        """Initialize the deployment manager.
        
        Args:
            server_manager: ServerManager instance.
        """
        self.server_manager = server_manager
        self.remote_base_dir = '/opt/telegram-tracker'
        self.service_name = 'telegram-tracker'
        self.service_file = f"{self.service_name}.service"
    
    def deploy(self, config_path: str) -> bool:
        """Deploy the Telegram tracker to the connected server.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            bool: True if deployment successful, False otherwise.
        """
        if not self.server_manager.ssh_client or not self.server_manager.current_server:
            print(f"{Colors.FAIL}Not connected to any server.{Colors.ENDC}")
            return False
        
        try:
            # Create remote directory
            self.server_manager.execute_command(f"mkdir -p {self.remote_base_dir}")
            
            # Upload files
            files_to_upload = [
                ('telegram_tracker.py', f"{self.remote_base_dir}/telegram_tracker.py"),
                (config_path, f"{self.remote_base_dir}/config.json"),
                ('requirements.txt', f"{self.remote_base_dir}/requirements.txt")
            ]
            
            for local_path, remote_path in files_to_upload:
                if not self.server_manager.upload_file(local_path, remote_path):
                    return False
            
            # Create systemd service file
            self._create_service_file()
            
            # Install dependencies
            print(f"{Colors.CYAN}Installing dependencies...{Colors.ENDC}")
            self.server_manager.execute_command("apt-get update")
            self.server_manager.execute_command("apt-get install -y python3 python3-pip")
            self.server_manager.execute_command(f"pip3 install -r {self.remote_base_dir}/requirements.txt")
            
            # Set permissions
            self.server_manager.execute_command(f"chmod +x {self.remote_base_dir}/telegram_tracker.py")
            
            # Enable and start service
            self.enable_service()
            self.start_service()
            
            print(f"{Colors.GREEN}Deployment completed successfully.{Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}Deployment failed: {e}{Colors.ENDC}")
            return False
    
    def _create_service_file(self) -> None:
        """Create systemd service file on the remote server."""
        service_content = f"""[Unit]
        Description=Telegram Online Status Tracker
        After=network.target
        
        [Service]
        Type=simple
        User=root
        WorkingDirectory={self.remote_base_dir}
        ExecStart=/usr/bin/python3 {self.remote_base_dir}/telegram_tracker.py
        Restart=on-failure
        RestartSec=10
        StandardOutput=syslog
        StandardError=syslog
        SyslogIdentifier={self.service_name}
        
        [Install]
        WantedBy=multi-user.target
        """
        
        # Remove leading whitespace from each line
        service_content = '\n'.join([line.strip() for line in service_content.split('\n')])
        
        # Create temporary file
        temp_file = 'temp_service_file'
        with open(temp_file, 'w') as f:
            f.write(service_content)
        
        # Upload to remote server
        self.server_manager.upload_file(temp_file, f"/etc/systemd/system/{self.service_file}")
        
        # Remove temporary file
        os.remove(temp_file)
        
        # Reload systemd
        self.server_manager.execute_command("systemctl daemon-reload")
    
    def start_service(self) -> bool:
        """Start the Telegram tracker service.
        
        Returns:
            bool: True if service started successfully, False otherwise.
        """
        stdout, stderr = self.server_manager.execute_command(f"systemctl start {self.service_name}")
        if not stderr:
            print(f"{Colors.GREEN}Service started successfully.{Colors.ENDC}")
            return True
        return False
    
    def stop_service(self) -> bool:
        """Stop the Telegram tracker service.
        
        Returns:
            bool: True if service stopped successfully, False otherwise.
        """
        stdout, stderr = self.server_manager.execute_command(f"systemctl stop {self.service_name}")
        if not stderr:
            print(f"{Colors.GREEN}Service stopped successfully.{Colors.ENDC}")
            return True
        return False
    
    def enable_service(self) -> bool:
        """Enable the Telegram tracker service to start on boot.
        
        Returns:
            bool: True if service enabled successfully, False otherwise.
        """
        stdout, stderr = self.server_manager.execute_command(f"systemctl enable {self.service_name}")
        if not stderr:
            print(f"{Colors.GREEN}Service enabled successfully.{Colors.ENDC}")
            return True
        return False
    
    def disable_service(self) -> bool:
        """Disable the Telegram tracker service from starting on boot.
        
        Returns:
            bool: True if service disabled successfully, False otherwise.
        """
        stdout, stderr = self.server_manager.execute_command(f"systemctl disable {self.service_name}")
        if not stderr:
            print(f"{Colors.GREEN}Service disabled successfully.{Colors.ENDC}")
            return True
        return False
    
    def get_service_status(self) -> str:
        """Get the status of the Telegram tracker service.
        
        Returns:
            str: Service status.
        """
        stdout, stderr = self.server_manager.execute_command(f"systemctl status {self.service_name}")
        return stdout
    
    def download_logs(self, local_dir: str = './logs') -> bool:
        """Download service logs from the connected server.
        
        Args:
            local_dir: Local directory to save logs.
            
        Returns:
            bool: True if logs downloaded successfully, False otherwise.
        """
        if not self.server_manager.ssh_client or not self.server_manager.current_server:
            print(f"{Colors.FAIL}Not connected to any server.{Colors.ENDC}")
            return False
        
        try:
            # Create local directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)
            
            # Get journal logs
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            journal_log_path = f"{local_dir}/{self.server_manager.current_server}_journal_{timestamp}.log"
            
            stdout, stderr = self.server_manager.execute_command(f"journalctl -u {self.service_name} -n 1000")
            with open(journal_log_path, 'w') as f:
                f.write(stdout)
            
            print(f"{Colors.GREEN}Journal logs saved to {journal_log_path}{Colors.ENDC}")
            
            # Download application log file if it exists
            remote_log_path = f"{self.remote_base_dir}/tracker.log"
            local_log_path = f"{local_dir}/{self.server_manager.current_server}_tracker_{timestamp}.log"
            
            # Check if remote log file exists
            stdout, stderr = self.server_manager.execute_command(f"test -f {remote_log_path} && echo 'exists'")
            if 'exists' in stdout:
                self.server_manager.download_file(remote_log_path, local_log_path)
                print(f"{Colors.GREEN}Application logs saved to {local_log_path}{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}Application log file not found on server.{Colors.ENDC}")
            
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}Failed to download logs: {e}{Colors.ENDC}")
            return False
    
    def download_database(self, local_dir: str = './data') -> bool:
        """Download the database from the connected server.
        
        Args:
            local_dir: Local directory to save the database.
            
        Returns:
            bool: True if database downloaded successfully, False otherwise.
        """
        if not self.server_manager.ssh_client or not self.server_manager.current_server:
            print(f"{Colors.FAIL}Not connected to any server.{Colors.ENDC}")
            return False
        
        try:
            # Create local directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)
            
            # Get database path from config
            stdout, stderr = self.server_manager.execute_command(f"cat {self.remote_base_dir}/config.json")
            if not stdout:
                print(f"{Colors.FAIL}Could not read config file.{Colors.ENDC}")
                return False
            
            try:
                config = json.loads(stdout)
                db_path = config.get('database', {}).get('path', 'tracker.db')
                
                # If path is relative, prepend remote base dir
                if not db_path.startswith('/'):
                    db_path = f"{self.remote_base_dir}/{db_path}"
                    
            except json.JSONDecodeError:
                print(f"{Colors.WARNING}Could not parse config JSON. Using default database path.{Colors.ENDC}")
                db_path = f"{self.remote_base_dir}/tracker.db"
            
            # Check if database file exists
            stdout, stderr = self.server_manager.execute_command(f"test -f {db_path} && echo 'exists'")
            if 'exists' not in stdout:
                print(f"{Colors.FAIL}Database file not found on server.{Colors.ENDC}")
                return False
            
            # Download database
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            local_db_path = f"{local_dir}/{self.server_manager.current_server}_db_{timestamp}.db"
            
            return self.server_manager.download_file(db_path, local_db_path)
            
        except Exception as e:
            print(f"{Colors.FAIL}Failed to download database: {e}{Colors.ENDC}")
            return False


class AdminCLI:
    """Interactive CLI for the Telegram tracker administration."""
    
    def __init__(self):
        """Initialize the admin CLI."""
        self.server_manager = ServerManager()
        self.deployment_manager = DeploymentManager(self.server_manager)
        self.running = True
    
    def _print_menu(self) -> None:
        """Print the main menu."""
        print(f"\n{Colors.HEADER}Telegram Tracker Administration{Colors.ENDC}")
        print(f"{Colors.BOLD}Server Management:{Colors.ENDC}")
        print("  1. List servers")
        print("  2. Add server")
        print("  3. Remove server")
        print("  4. Connect to server")
        print("  5. Disconnect from server")
        
        print(f"\n{Colors.BOLD}Deployment:{Colors.ENDC}")
        print("  6. Deploy tracker")
        
        print(f"\n{Colors.BOLD}Service Management:{Colors.ENDC}")
        print("  7. Start service")
        print("  8. Stop service")
        print("  9. Enable service")
        print(" 10. Disable service")
        print(" 11. Get service status")
        
        print(f"\n{Colors.BOLD}Data Management:{Colors.ENDC}")
        print(" 12. Download logs")
        print(" 13. Download database")
        
        print(f"\n{Colors.BOLD}Other:{Colors.ENDC}")
        print(" 14. Execute custom command")
        print(" 15. Exit")
        
        if self.server_manager.current_server:
            print(f"\n{Colors.GREEN}Connected to: {self.server_manager.current_server}{Colors.ENDC}")
        else:
            print(f"\n{Colors.WARNING}Not connected to any server{Colors.ENDC}")
    
    def _get_choice(self) -> int:
        """Get user choice from the menu.
        
        Returns:
            int: User choice.
        """
        try:
            choice = input(f"\n{Colors.BOLD}Enter your choice (1-15): {Colors.ENDC}")
            return int(choice)
        except ValueError:
            return 0
    
    def run(self) -> None:
        """Run the interactive CLI."""
        print(f"{Colors.GREEN}Welcome to the Telegram Tracker Administration CLI!{Colors.ENDC}")
        
        while self.running:
            self._print_menu()
            choice = self._get_choice()
            
            if choice == 1:
                self.server_manager.list_servers()
            elif choice == 2:
                self._add_server()
            elif choice == 3:
                self._remove_server()
            elif choice == 4:
                self._connect_to_server()
            elif choice == 5:
                self.server_manager.disconnect()
            elif choice == 6:
                self._deploy_tracker()
            elif choice == 7:
                self.deployment_manager.start_service()
            elif choice == 8:
                self.deployment_manager.stop_service()
            elif choice == 9:
                self.deployment_manager.enable_service()
            elif choice == 10:
                self.deployment_manager.disable_service()
            elif choice == 11:
                status = self.deployment_manager.get_service_status()
                print(f"\n{status}")
            elif choice == 12:
                self._download_logs()
            elif choice == 13:
                self._download_database()
            elif choice == 14:
                self._execute_custom_command()
            elif choice == 15:
                self._exit()
            else:
                print(f"{Colors.FAIL}Invalid choice. Please try again.{Colors.ENDC}")
            
            # Pause before showing menu again
            if self.running:
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
    
    def _add_server(self) -> None:
        """Add a new server."""
        print(f"\n{Colors.HEADER}Add Server{Colors.ENDC}")
        name = input("Enter server name/alias: ")
        ip = input("Enter server IP address: ")
        username = input("Enter SSH username: ")
        password = getpass.getpass("Enter SSH password: ")
        
        self.server_manager.add_server(name, ip, username, password)
    
    def _remove_server(self) -> None:
        """Remove a server."""
        print(f"\n{Colors.HEADER}Remove Server{Colors.ENDC}")
        self.server_manager.list_servers()
        name = input("Enter server name to remove: ")
        
        self.server_manager.remove_server(name)
    
    def _connect_to_server(self) -> None:
        """Connect to a server."""
        print(f"\n{Colors.HEADER}Connect to Server{Colors.ENDC}")
        self.server_manager.list_servers()
        name = input("Enter server name to connect to: ")
        
        self.server_manager.connect(name)
    
    def _deploy_tracker(self) -> None:
        """Deploy the Telegram tracker."""
        print(f"\n{Colors.HEADER}Deploy Tracker{Colors.ENDC}")
        
        if not self.server_manager.current_server:
            print(f"{Colors.FAIL}Not connected to any server. Please connect first.{Colors.ENDC}")
            return
        
        config_path = input("Enter path to config.json (default: config.json): ") or "config.json"
        
        if not os.path.exists(config_path):
            print(f"{Colors.FAIL}Config file not found: {config_path}{Colors.ENDC}")
            return
        
        self.deployment_manager.deploy(config_path)
    
    def _download_logs(self) -> None:
        """Download logs from the server."""
        print(f"\n{Colors.HEADER}Download Logs{Colors.ENDC}")
        
        if not self.server_manager.current_server:
            print(f"{Colors.FAIL}Not connected to any server. Please connect first.{Colors.ENDC}")
            return
        
        local_dir = input("Enter local directory to save logs (default: ./logs): ") or "./logs"
        
        self.deployment_manager.download_logs(local_dir)
    
    def _download_database(self) -> None:
        """Download the database from the server."""
        print(f"\n{Colors.HEADER}Download Database{Colors.ENDC}")
        
        if not self.server_manager.current_server:
            print(f"{Colors.FAIL}Not connected to any server. Please connect first.{Colors.ENDC}")
            return
        
        local_dir = input("Enter local directory to save database (default: ./data): ") or "./data"
        
        self.deployment_manager.download_database(local_dir)
    
    def _execute_custom_command(self) -> None:
        """Execute a custom command on the server."""
        print(f"\n{Colors.HEADER}Execute Custom Command{Colors.ENDC}")
        
        if not self.server_manager.current_server:
            print(f"{Colors.FAIL}Not connected to any server. Please connect first.{Colors.ENDC}")
            return
        
        command = input("Enter command to execute: ")
        
        self.server_manager.execute_command(command)
    
    def _exit(self) -> None:
        """Exit the CLI."""
        print(f"\n{Colors.GREEN}Exiting...{Colors.ENDC}")
        self.server_manager.disconnect()
        self.running = False


def main() -> None:
    """Main entry point for the application."""
    try:
        cli = AdminCLI()
        cli.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrupted by user.{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}")
    finally:
        print(f"{Colors.GREEN}Goodbye!{Colors.ENDC}")


if __name__ == "__main__":
    main()