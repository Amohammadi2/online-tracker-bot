#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from telethon import TelegramClient
from telethon.tl.types import User, UserStatusOnline, UserStatusOffline, UserStatusRecently
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.users import GetUsersRequest


class ConfigManager:
    """Manages the configuration for the Telegram tracker."""
    
    def __init__(self, config_path: str = 'config.json'):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file.
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger('ConfigManager')
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from the JSON file.
        
        Returns:
            Dict containing the configuration.
        """
        try:
            self.logger.info(f"Loading configuration from {self.config_path}")
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Configuration file {self.config_path} not found. Creating default configuration.")
                self._create_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                self.logger.info(f"Configuration loaded successfully")
                return self.config
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def _create_default_config(self) -> None:
        """Create a default configuration file."""
        default_config = {
            "telegram": {
                "api_id": "YOUR_API_ID",
                "api_hash": "YOUR_API_HASH",
                "phone": "YOUR_PHONE_NUMBER"
            },
            "tracking": {
                "user_ids": [12345, 67890],  # Example user IDs to track
                "check_interval": 60  # Check status every 60 seconds
            },
            "database": {
                "path": "tracker.db"
            },
            "logging": {
                "level": "INFO",
                "file": "tracker.log",  # Set to null or empty string to disable file logging
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "rate_limiting": {
                "max_requests_per_second": 25  # Stay below Telegram's limit of 30
            }
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
                self.logger.info(f"Default configuration created at {self.config_path}")
        except Exception as e:
            self.logger.error(f"Error creating default configuration: {e}")
            raise


class DatabaseManager:
    """Manages the SQLite database operations."""
    
    def __init__(self, db_path: str):
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.logger = logging.getLogger('DatabaseManager')
    
    def initialize(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        try:
            self.logger.info(f"Initializing database at {self.db_path}")
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create status table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT,
                was_online TIMESTAMP,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            self.conn.commit()
            self.logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.logger.info("Closing database connection")
            self.conn.close()
            self.conn = None
    
    def update_user(self, user: User) -> None:
        """Update or insert user information.
        
        Args:
            user: Telethon User object.
        """
        if not self.conn:
            self.logger.error("Database connection not initialized")
            return
        
        try:
            self.logger.info(f"Updating user information for user_id={user.id}")
            cursor = self.conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = ?", (user.id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing user
                cursor.execute('''
                UPDATE users 
                SET username = ?, first_name = ?, last_name = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
                ''', (user.username, user.first_name, user.last_name, user.id))
                self.logger.debug(f"Updated existing user: {user.id}")
            else:
                # Insert new user
                cursor.execute('''
                INSERT INTO users (id, username, first_name, last_name) 
                VALUES (?, ?, ?, ?)
                ''', (user.id, user.username, user.first_name, user.last_name))
                self.logger.debug(f"Inserted new user: {user.id}")
            
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error updating user {user.id}: {e}")
            self.conn.rollback()
    
    def record_status(self, user_id: int, status: str, was_online: Optional[datetime] = None) -> None:
        """Record a user's online status.
        
        Args:
            user_id: Telegram user ID.
            status: Status string ('online', 'offline', 'recently', etc.)
            was_online: Timestamp when the user was last seen online.
        """
        if not self.conn:
            self.logger.error("Database connection not initialized")
            return
        
        try:
            self.logger.info(f"Recording status for user_id={user_id}: {status}")
            cursor = self.conn.cursor()
            
            if was_online:
                cursor.execute('''
                INSERT INTO status (user_id, status, was_online) 
                VALUES (?, ?, ?)
                ''', (user_id, status, was_online.isoformat()))
            else:
                cursor.execute('''
                INSERT INTO status (user_id, status) 
                VALUES (?, ?)
                ''', (user_id, status))
            
            self.conn.commit()
            self.logger.debug(f"Status recorded for user {user_id}")
        except sqlite3.Error as e:
            self.logger.error(f"Error recording status for user {user_id}: {e}")
            self.conn.rollback()


class RateLimiter:
    """Implements rate limiting for API requests."""
    
    def __init__(self, max_requests_per_second: int):
        """Initialize the rate limiter.
        
        Args:
            max_requests_per_second: Maximum number of requests allowed per second.
        """
        self.max_requests = max_requests_per_second
        self.interval = 1.0  # 1 second
        self.request_times: List[float] = []
        self.logger = logging.getLogger('RateLimiter')
    
    async def wait_if_needed(self) -> None:
        """Wait if the rate limit would be exceeded."""
        current_time = time.time()
        
        # Remove timestamps older than our interval
        self.request_times = [t for t in self.request_times if current_time - t <= self.interval]
        
        # If we've hit our limit, wait until we can make another request
        if len(self.request_times) >= self.max_requests:
            oldest_request = min(self.request_times)
            wait_time = self.interval - (current_time - oldest_request)
            
            if wait_time > 0:
                self.logger.debug(f"Rate limit reached. Waiting for {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Add the current request time
        self.request_times.append(time.time())


class TelegramTracker:
    """Main class for tracking Telegram users' online status."""
    
    def __init__(self, config_path: str = 'config.json'):
        """Initialize the Telegram tracker.
        
        Args:
            config_path: Path to the configuration file.
        """
        # Set up logging first so we can log initialization
        self._setup_default_logging()
        self.logger = logging.getLogger('TelegramTracker')
        
        self.logger.info("Initializing Telegram Tracker")
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Now that we have the config, update logging configuration
        self._setup_logging_from_config()
        
        # Initialize components
        db_path = self.config['database']['path']
        self.db_manager = DatabaseManager(db_path)
        
        # Initialize rate limiter
        max_requests = self.config['rate_limiting']['max_requests_per_second']
        self.rate_limiter = RateLimiter(max_requests)
        
        # Initialize Telegram client
        api_id = self.config['telegram']['api_id']
        api_hash = self.config['telegram']['api_hash']
        phone = self.config['telegram']['phone']
        
        self.client = TelegramClient('tracker_session', api_id, api_hash)
        self.phone = phone
        self.user_ids = self.config['tracking']['user_ids']
        self.check_interval = self.config['tracking']['check_interval']
        
        self.is_running = False
    
    def _setup_default_logging(self) -> None:
        """Set up default logging before config is loaded."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
    
    def _setup_logging_from_config(self) -> None:
        """Set up logging based on the loaded configuration."""
        log_config = self.config['logging']
        log_level = getattr(logging, log_config['level'].upper())
        log_format = log_config['format']
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:  # Make a copy of the list
            root_logger.removeHandler(handler)
        
        # Set up new handlers
        handlers = [logging.StreamHandler()]
        
        # Add file handler if configured
        log_file = log_config.get('file')
        if log_file and log_file.strip():
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                handlers.append(file_handler)
                self.logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                self.logger.error(f"Failed to set up file logging: {e}")
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers
        )
        
        self.logger.info(f"Logging configured with level {log_config['level']}")
    
    async def start(self) -> None:
        """Start the Telegram tracker."""
        try:
            self.logger.info("Starting Telegram Tracker")
            self.db_manager.initialize()
            
            # Connect to Telegram
            self.logger.info("Connecting to Telegram")
            await self.client.start(phone=self.phone, password="ashkan@31")
            self.logger.info("Connected to Telegram successfully")
            
            self.is_running = True
            await self._tracking_loop()
        except Exception as e:
            self.logger.error(f"Error starting tracker: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the Telegram tracker."""
        self.logger.info("Stopping Telegram Tracker")
        self.is_running = False
        
        if self.client.is_connected():
            await self.client.disconnect()
            self.logger.info("Disconnected from Telegram")
        
        self.db_manager.close()
        self.logger.info("Telegram Tracker stopped")
    
    async def _tracking_loop(self) -> None:
        """Main tracking loop that periodically checks users' status."""
        self.logger.info(f"Starting tracking loop for {len(self.user_ids)} users")
        self.logger.info(f"Check interval: {self.check_interval} seconds")
        
        while self.is_running:
            try:
                await self._check_all_users()
                self.logger.info(f"Sleeping for {self.check_interval} seconds")
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                self.logger.info("Tracking loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in tracking loop: {e}")
                # Sleep a bit to avoid tight error loops
                await asyncio.sleep(5)
    
    async def _check_all_users(self) -> None:
        """Check the status of all tracked users."""
        self.logger.info(f"Checking status for {len(self.user_ids)} users")
        
        try:
            # Apply rate limiting once for the batch request
            await self.rate_limiter.wait_if_needed()
            
            # Batch request for all users
            self.logger.info(f"Fetching information for {len(self.user_ids)} users in batch")
            users = await self.client(GetUsersRequest(id=self.user_ids))
            
            # Process each user
            for user in users:
                try:
                    # Update user info in database
                    self.db_manager.update_user(user)
                    
                    # Get and record status
                    await self._record_user_status(user)
                    
                except Exception as e:
                    self.logger.error(f"Error processing user_id={user.id}: {e}")
                
        except FloodWaitError as e:
            wait_time = e.seconds
            self.logger.warning(f"Hit Telegram rate limit. Waiting for {wait_time} seconds")
            await asyncio.sleep(wait_time)
        except RPCError as e:
            self.logger.error(f"Telegram RPC error during batch user fetch: {e}")
        except Exception as e:
            self.logger.error(f"Error during batch user fetch: {e}")
            # Fall back to individual requests if batch fails
            self.logger.info("Falling back to individual user requests")
            await self._check_users_individually()
    
    async def _check_users_individually(self) -> None:
        """Fallback method to check users individually if batch request fails."""
        for user_id in self.user_ids:
            try:
                # Apply rate limiting
                await self.rate_limiter.wait_if_needed()
                
                # Get user info and status
                self.logger.info(f"Checking status for user_id={user_id}")
                user = await self.client.get_entity(user_id)
                
                # Update user info in database
                self.db_manager.update_user(user)
                
                # Get and record status
                await self._record_user_status(user)
                
            except FloodWaitError as e:
                wait_time = e.seconds
                self.logger.warning(f"Hit Telegram rate limit. Waiting for {wait_time} seconds")
                await asyncio.sleep(wait_time)
            except RPCError as e:
                self.logger.error(f"Telegram RPC error for user_id={user_id}: {e}")
            except Exception as e:
                self.logger.error(f"Error checking user_id={user_id}: {e}")
    
    async def _record_user_status(self, user: User) -> None:
        """Record a user's status in the database.
        
        Args:
            user: Telethon User object.
        """
        status_obj = user.status
        status_str = "unknown"
        was_online = None
        
        if isinstance(status_obj, UserStatusOnline):
            status_str = "online"
            self.logger.info(f"User {user.id} is online")
        elif isinstance(status_obj, UserStatusOffline):
            status_str = "offline"
            was_online = status_obj.was_online
            self.logger.info(f"User {user.id} is offline, last seen: {was_online}")
        elif isinstance(status_obj, UserStatusRecently):
            status_str = "recently"
            self.logger.info(f"User {user.id} was online recently")
        else:
            self.logger.info(f"User {user.id} has status: {status_obj.__class__.__name__}")
        
        # Record in database
        self.db_manager.record_status(user.id, status_str, was_online)


async def main() -> None:
    """Main entry point for the application."""
    # Default config path
    config_path = 'config.json'
    
    # Allow overriding config path from command line
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    tracker = TelegramTracker(config_path)
    
    try:
        await tracker.start()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if tracker.is_running:
            await tracker.stop()


if __name__ == "__main__":
    asyncio.run(main())