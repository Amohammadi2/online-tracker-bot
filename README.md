# Telegram Online Status Tracker

This script tracks the online status of Telegram users and stores the data in a SQLite database. It uses the Telethon library to interact with the Telegram API.

## Features

- Track online status of multiple Telegram users
- Store user data and status history in SQLite database
- Configurable via JSON configuration file
- Detailed logging with console and optional file output
- Rate limiting to avoid hitting Telegram API limits
- Robust error handling to prevent crashes

## Requirements

- Python 3.6+
- Telethon library
- SQLite3 (included in Python standard library)

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install telethon
```

## Configuration

The script uses a JSON configuration file (`config.json` by default). If the file doesn't exist, a default configuration will be created on first run.

Example configuration:

```json
{
    "telegram": {
        "api_id": "YOUR_API_ID",
        "api_hash": "YOUR_API_HASH",
        "phone": "YOUR_PHONE_NUMBER"
    },
    "tracking": {
        "user_ids": [12345, 67890],
        "check_interval": 60
    },
    "database": {
        "path": "tracker.db"
    },
    "logging": {
        "level": "INFO",
        "file": "tracker.log",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "rate_limiting": {
        "max_requests_per_second": 25
    }
}
```

### Configuration Options

- **telegram**
  - `api_id`: Your Telegram API ID (get from https://my.telegram.org)
  - `api_hash`: Your Telegram API hash
  - `phone`: Your phone number in international format

- **tracking**
  - `user_ids`: Array of Telegram user IDs to track
  - `check_interval`: Time in seconds between status checks

- **database**
  - `path`: Path to the SQLite database file

- **logging**
  - `level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - `file`: Path to log file (set to empty string to disable file logging)
  - `format`: Log message format

- **rate_limiting**
  - `max_requests_per_second`: Maximum API requests per second (stay below Telegram's limit of 30)

## Usage

Run the script with:

```bash
python telegram_tracker.py
```

You can specify a custom configuration file path:

```bash
python telegram_tracker.py /path/to/custom_config.json
```

## Database Schema

The script creates two tables in the SQLite database:

1. **users** - Stores user information
   - id: Telegram user ID (primary key)
   - username: Telegram username
   - first_name: User's first name
   - last_name: User's last name
   - phone: User's phone number (if available)
   - updated_at: Timestamp of last update

2. **status** - Stores status history
   - id: Auto-incrementing primary key
   - user_id: Telegram user ID (foreign key to users table)
   - status: Status string ('online', 'offline', 'recently', etc.)
   - was_online: Timestamp when user was last seen online (for offline status)
   - recorded_at: Timestamp when status was recorded

## Error Handling

The script includes comprehensive error handling to prevent crashes:
- Telegram API rate limiting
- Network errors
- Database errors
- Configuration errors

## License

MIT


## Administration Script

The project includes an administration script (`admin.py`) that allows you to easily deploy and manage the tracker on remote servers.

### Features

- **Server Management**
  - Store server credentials securely (IP, username, password)
  - Add, remove, and list servers
  - Connect to and disconnect from servers

- **Deployment**
  - Deploy the tracker bot to remote servers
  - Upload necessary files (tracker script, config, requirements)
  - Install dependencies automatically
  - Set up systemd service for automatic startup

- **Service Management**
  - Start, stop, enable, and disable the systemd service
  - Get service status

- **Data Management**
  - Download log files from the server
  - Download the database file for backup or analysis

### Requirements

- Python 3.12+
- Paramiko library (for SSH/SFTP functionality)

### Installation

Install the required dependencies for the administration script:

```bash
pip install -r admin_requirements.txt
```

### Usage

Run the administration script:

```bash
python admin.py
```

This will launch an interactive CLI with the following options:

1. **Server Management**
   - List servers
   - Add server
   - Remove server
   - Connect to server
   - Disconnect from server

2. **Deployment**
   - Deploy tracker

3. **Service Management**
   - Start service
   - Stop service
   - Enable service
   - Disable service
   - Get service status

4. **Data Management**
   - Download logs
   - Download database

5. **Other**
   - Execute custom command
   - Exit

### Deployment Process

When deploying the tracker to a server, the script will:

1. Upload all necessary files to `/opt/telegram-tracker/`
2. Install required dependencies
3. Create and enable a systemd service
4. Start the service

The systemd service will ensure that the tracker starts automatically on system boot and restarts if it crashes.