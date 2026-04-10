# HarmonyOS App Installer - Modern GUI Tool

A modern graphical installer for Huawei HarmonyOS applications with multi-version support, server-based management, and Chinese localization.

## Features

- **Modern GUI Interface**: Beautiful and intuitive user interface with dark theme
- **Multi-Application Support**: Manage multiple HarmonyOS applications
- **Version Management**: Each application supports multiple versions with selection
- **Server-Based Architecture**: Centralized server for application and version management
- **Cross-Platform Support**: Windows, macOS, Linux compatibility
- **Chinese Localization**: Full Chinese interface and messages
- **Automatic HDC Detection**: Automatically detects and selects appropriate HDC tools
- **Real-time Logging**: Detailed operation process and error information
- **One-Click Installation**: Automated installation process with error handling
- **Web Admin Panel**: Browser-based administration interface

## Architecture

### Client-Server Structure
- **Client**: `harmony_ultra_modern.py` - Modern GUI application
- **Server**: `server/` directory - Flask-based REST API server
- **Admin Panel**: `server/admin.html` - Web-based management interface

### Key Components

#### Client Features
- Modern Tkinter GUI with dark theme
- Application list and version selection
- Real-time installation progress
- Device status monitoring
- Chinese localized interface

#### Server Features
- RESTful API for application management
- File upload and version management
- SQLite database for metadata
- Web-based admin panel
- File serving for client downloads

## Installation

### Prerequisites
- Python 3.7+
- HDC tools (included in project)
- Modern web browser for admin panel

### Setup Server
```bash
cd server
pip install -r requirements.txt
python app.py
```

The server will start on `http://localhost:5000`

### Setup Client

#### Method 1: Run Python Script
```bash
python harmony_ultra_modern.py
```

#### Method 2: Build Executable (Recommended)
```bash
pip install pyinstaller
pyinstaller harmony_app_installer.spec
```

The executable will be in `dist/HarmonyOSInstaller.exe`

## Usage

### Using the GUI Client
1. **Start the Client**: Run `HarmonyOSInstaller.exe` or Python script
2. **Configure Server**: Set server URL in configuration
3. **Connect Device**: Connect HarmonyOS device via USB with developer mode
4. **Select Application**: Choose from application list
5. **Select Version**: Choose specific version to install
6. **Install**: Click "Install Selected Version" button
7. **Monitor Progress**: Watch real-time installation logs

### Using the Web Admin Panel
1. **Access Admin Panel**: Open `http://localhost:5000/admin`
2. **Manage Applications**: Add/edit applications
3. **Upload Versions**: Upload HAP/HSP files
4. **Configure Settings**: Manage server configuration

## Project Structure

```
harmony_test_pkg/
|   harmony_ultra_modern.py      # Main GUI client
|   HarmonyOSInstaller.exe      # Compiled executable
|   harmony_app_installer.spec   # PyInstaller specification
|   README.md                    # This file
|   .gitignore                   # Git ignore file
|   
+---server/                      # Server directory
|   |   app.py                   # Flask server application
|   |   admin.html               # Web admin panel
|   |   requirements.txt         # Server dependencies
|   |   .gitignore               # Server git ignore
|   |   README.md                # Server documentation
|   |   
|   +---api/                     # API endpoints
|   |   |   apps.py               # Application management API
|   |   |   files.py              # File upload/download API
|   |   |   versions.py           # Version management API
|   |   |   __init__.py           # API initialization
|   |   
|   +---database/                # Database components
|   |   |   models.py             # Database models
|   |   |   __init__.py           # Database initialization
|   |   
|   +---uploads/                  # Upload directory (uploads/apps/<app_id>/<version_id>/...)
|   
+---hdc_arm/                     # ARM architecture HDC tools
+---hdc_win/                     # Windows HDC tools  
+---hdc_x86/                     # x86 architecture HDC tools
+---build/                       # PyInstaller build files
+---dist/                        # Distribution directory
```

## API Endpoints

### Application Management
- `GET /api/apps` - List all applications
- `POST /api/apps` - Create new application
- `PUT /api/apps/{id}` - Update application
- `DELETE /api/apps/{id}` - Delete application

### Version Management
- `GET /api/apps/{app_id}/versions` - List application versions
- `POST /api/apps/{app_id}/versions` - Create new version
- `PUT /api/versions/{id}` - Update version
- `DELETE /api/versions/{id}` - Delete version
- `GET /api/versions/{id}/info` - Get version info (compat format)
- `DELETE /api/versions/{version_id}/files/{file_type}` - Delete a specific file type (hap/hsp)

#### Create Version with Upload (Fields + Files)

Create (or overwrite) an app version and upload both HAP/HSP files in a single request.

- **Method/URL**: `POST /api/versions/create-with-files`
- **Content-Type**: `multipart/form-data`

Form fields:
- `app_id` (required, int)
- `version` (required, string)
- `description` (optional)
- `release_date` (optional, e.g. `2026-04-10`)
- `deploy_path` (optional, default: `/data/local/tmp`)
- `set_as_current` (optional, `true/false` or `1/0`)

Files:
- `hap_file` (required, `.hap`)
- `hsp_file` (required, `.hsp`)

Overwrite rule:
- A version is considered duplicate by `(app_id, version)`.
- If it already exists, the server overwrites the existing version's `hap/hsp` records (only one file per type is kept).

Example (Windows PowerShell curl):
```powershell
curl -X POST "http://127.0.0.1:5000/api/versions/create-with-files" `
  -F "app_id=1" `
  -F "version=1.0.2" `
  -F "description=second release" `
  -F "release_date=2026-04-10" `
  -F "deploy_path=/data/local/tmp" `
  -F "set_as_current=true" `
  -F "hap_file=@C:\path\to\debug1.hap" `
  -F "hsp_file=@C:\path\to\tztzfnetwork-signed1.hsp"
```

Example (Python):
```python
import requests

url = "http://127.0.0.1:5000/api/versions/create-with-files"

data = {
    "app_id": "1",
    "version": "1.0.2",
    "description": "second release",
    "release_date": "2026-04-10",
    "deploy_path": "/data/local/tmp",
    "set_as_current": "true",
}

files = {
    "hap_file": open(r"C:\path\to\debug1.hap", "rb"),
    "hsp_file": open(r"C:\path\to\tztzfnetwork-signed1.hsp", "rb"),
}

resp = requests.post(url, data=data, files=files, timeout=300)
print(resp.status_code)
print(resp.text)
```

Response:
- **Success**: HTTP `201`, returns the version object and `files` map, without an `error` field.
- **Failure**: HTTP `400/404/500`, returns JSON `{ "error": "..." }`.

### File Management
- `POST /api/upload` - Upload a file to an existing version (multipart)
- `GET /api/files/{id}` - Download file by file id
- `DELETE /api/files/{id}` - Delete file by file id
- `GET /api/versions/{version_id}/files/{file_type}/download` - Download a version's specific file (hap/hsp)
- `GET /files/{filename}` - Download by filename (legacy/compat)

## Installation Process

The automated installation process includes:
1. **Stop Application**: `shell aa force-stop {bundle_name}`
2. **Uninstall Old Version**: `shell bm uninstall -n {bundle_name} -k`
3. **Upload HSP**: `file send {hsp_file} {deploy_path}`
4. **Upload HAP**: `file send {hap_file} {deploy_path}`
5. **Install HSP**: `shell bm install -p {deploy_path}/{hsp_file}`
6. **Install HAP**: `shell bm install -p {deploy_path}/{hap_file}`
7. **Start Application**: `shell aa start -a {main_ability} -b {bundle_name} -m entry`

## Configuration

### Client Configuration
- Server URL configuration
- Download directory settings
- HDC tool path detection
- Language settings (Chinese/English)

### Server Configuration
- Database settings
- File storage paths
- Upload limits
- API endpoints

## Troubleshooting

### HDC Tool Issues
- Ensure HDC tools are in correct directories
- Check device connection and USB debugging
- Verify developer mode is enabled

### Server Issues
- Check Flask server is running
- Verify database permissions
- Ensure file directories exist

### Installation Issues
- Check device storage space
- Verify HAP/HSP file integrity
- Review error logs in client

## Recent Updates

### v3.0 (Latest)
- **Modern GUI**: Complete interface redesign with dark theme
- **Chinese Localization**: Full Chinese interface support
- **Server Architecture**: Client-server architecture with REST API
- **Web Admin Panel**: Browser-based management interface
- **Version Selection**: Dynamic version information display
- **Error Handling**: Improved error handling and user feedback
- **Installation Optimization**: Fixed installation order and path issues

### v2.0
- Multi-application support
- Version management features
- Improved interface layout
- Configuration file management

### v1.0
- Initial GUI release
- Cross-platform HDC detection
- Real-time logging
- Basic installation features

## Requirements

### System Requirements
- Python 3.7+
- 4GB+ RAM
- 100MB+ disk space
- USB connection for device

### Dependencies
- **Client**: tkinter, requests, subprocess
- **Server**: Flask, SQLite3, Werkzeug

## License

MIT License - Free to use and modify

## Support

For issues and support:
1. Check troubleshooting section
2. Review error logs
3. Verify server connection
4. Check device compatibility

---

**Note**: This tool is designed specifically for Huawei HarmonyOS application development and testing. Ensure proper development environment setup before use.
