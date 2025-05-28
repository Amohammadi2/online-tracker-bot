# Telegram Online Status Tracker

## Overview

Telegram Online Status Tracker is a Python-based tool that monitors and records the online status of Telegram users. The application connects to the Telegram API, periodically checks the status of specified users, and stores this information in a SQLite database for later analysis or reference.

## Features

- Track online/offline status of multiple Telegram users
- Record status history with timestamps in a SQLite database
- Deploy and manage the tracker on remote servers using the admin CLI
- Automatic service management via systemd on remote servers
- Rate limiting to prevent hitting Telegram API restrictions

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git (for cloning the repository)

### Setting Up the Tracker

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/online-tracker-bot.git
   cd online-tracker-bot
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a configuration file:
   - The application will create a default `config.json` file on first run
   - Alternatively, you can create it manually following the template below

4. Configure your Telegram API credentials:
   - Obtain your API ID and API Hash from [my.telegram.org](https://my.telegram.org)
   - Update the `config.json` file with your credentials

### Configuration Template

```json
{
    "telegram": {
        "api_id": "YOUR_API_ID",
        "api_hash": "YOUR_API_HASH",
        "phone": "YOUR_PHONE_NUMBER"
    },
    "tracking": {
        "user_ids": [1234567890, "@another_user"],
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

### Running the Tracker Locally

Start the tracker with:

```bash
python telegram_tracker.py
```

You can specify a custom configuration file path:

```bash
python telegram_tracker.py /path/to/custom_config.json
```

## Admin CLI Setup and Usage

The Admin CLI tool allows you to deploy and manage the tracker on remote servers without manual setup.

### Setting Up the Admin CLI

1. Install the required dependencies for the admin script:
   ```bash
   pip install -r admin_requirements.txt
   ```

2. Run the admin script:
   ```bash
   python admin.py
   ```

### Managing Servers

#### Adding a Server

1. From the main menu, select **Server Management** → **Add server**
2. Enter the requested information:
   - Server name (an alias for easy reference)
   - IP address
   - Username (must have sudo privileges)
   - Password

#### Connecting to a Server

1. From the main menu, select **Server Management** → **Connect to server**
2. Choose a server from the list

### Deploying the Tracker

1. Connect to a server (as described above)
2. From the main menu, select **Deployment** → **Deploy tracker**
3. The script will:
   - Upload all necessary files to `/opt/telegram-tracker/`
   - Install required dependencies
   - Create a systemd service for automatic startup
   - Start the service

### Managing the Service

After deployment, you can manage the tracker service:

1. **Start the service**:
   - From the main menu, select **Service Management** → **Start service**

2. **Stop the service**:
   - From the main menu, select **Service Management** → **Stop service**

3. **Enable service autostart**:
   - From the main menu, select **Service Management** → **Enable service**

4. **Disable service autostart**:
   - From the main menu, select **Service Management** → **Disable service**

5. **Check service status**:
   - From the main menu, select **Service Management** → **Get service status**

### Managing Data

1. **Download logs**:
   - From the main menu, select **Data Management** → **Download logs**
   - The logs will be downloaded to your local machine

2. **Download database**:
   - From the main menu, select **Data Management** → **Download database**
   - The database will be downloaded to your local machine for analysis

### Executing Custom Commands

If you need to perform custom operations on the server:

1. From the main menu, select **Other** → **Execute custom command**
2. Enter the command to execute

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Ensure your Telegram API credentials are correct in the config file

2. **Connection Errors**: Check your internet connection and verify the server is accessible

3. **Permission Denied**: Ensure the user account has sudo privileges on the remote server

4. **Service Won't Start**: Check the logs for errors using the **Download logs** option

### Getting Help

If you encounter issues not covered in this documentation, please:

1. Check the log files for detailed error messages
2. Ensure all configuration parameters are set correctly
3. Verify that your server meets all the requirements

## License

MIT