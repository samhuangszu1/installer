# HarmonyOS Installer - Database Version

## Overview

This is the database-powered version of the HarmonyOS Installer API. It replaces the JSON file-based storage with a SQLite database, providing better scalability, data integrity, and management capabilities.

## Features

- **Database Storage**: SQLite database for applications, versions, and files
- **RESTful API**: Full CRUD operations for all entities
- **File Management**: Secure file upload and download
- **Admin Panel**: Web-based management interface
- **Legacy Compatibility**: Supports existing client applications
- **Data Migration**: Easy migration from JSON files

## Architecture

```
Frontend (GUI)        Admin Panel
       |                   |
       v                   v
    REST API
       |
       v
    SQLite Database
```

## Database Schema

### Apps Table
```sql
CREATE TABLE apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    bundle_name VARCHAR(255) NOT NULL,
    main_ability VARCHAR(255) NOT NULL,
    current_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Versions Table
```sql
CREATE TABLE versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    release_date DATE,
    size INTEGER,
    hap_filename VARCHAR(255),
    hsp_filename VARCHAR(255),
    deploy_path VARCHAR(500) DEFAULT '/data/local/tmp',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE
);
```

### Files Table
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    file_type VARCHAR(20) NOT NULL CHECK (file_type IN ('hap', 'hsp')),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (version_id) REFERENCES versions(id) ON DELETE CASCADE
);
```

## API Endpoints

### Applications Management
- `GET /api/apps` - Get all applications
- `POST /api/apps` - Create new application
- `PUT /api/apps/{id}` - Update application
- `DELETE /api/apps/{id}` - Delete application

### Versions Management
- `GET /api/apps/{app_id}/versions` - Get application versions
- `POST /api/apps/{app_id}/versions` - Create new version
- `PUT /api/versions/{id}` - Update version
- `DELETE /api/versions/{id}` - Delete version
- `GET /api/versions/{id}/info` - Get version info (legacy format)

### Files Management
- `POST /api/upload` - Upload file
- `GET /api/files/{id}` - Download file
- `DELETE /api/files/{id}` - Delete file
- `GET /api/versions/{id}/files/{type}/download` - Download version file

### Legacy Endpoints (for compatibility)
- `GET /apps` - Get applications (legacy format)
- `GET /apps/{app_id}/versions/{version}` - Get version info (legacy format)

### System Endpoints
- `GET /health` - Health check
- `GET /admin` - Admin panel
- `GET /` - API documentation

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. **Install dependencies**:
```bash
pip install -r requirements_db.txt
```

2. **Run data migration** (if upgrading from JSON version):
```bash
python migrate.py
```

3. **Start the server**:
```bash
python app_db.py
```

The server will start on `http://localhost:5000`

## Admin Panel

Access the admin panel at `http://localhost:5000/admin`

Features:
- View statistics (apps, versions, files)
- Manage applications (create, edit, delete)
- Manage versions (create, edit, delete)
- Upload files (HAP, HSP)
- Real-time data updates

## File Upload

Files are stored in the `uploads/apps/{app_id}/{version_id}/` directory structure.

Supported file types:
- `.hap` - HarmonyOS Application Package
- `.hsp` - HarmonyOS Shared Package

## Data Migration

If you're upgrading from the JSON-based version, run the migration script:

```bash
python migrate.py
```

The script will:
- Read existing `apps.json` and version files
- Convert them to database format
- Preserve file locations
- Show migration statistics

## Client Compatibility

The database version maintains full compatibility with existing client applications:

1. **Legacy endpoints** provide the same JSON format
2. **File download URLs** remain unchanged
3. **API responses** maintain the same structure

## Configuration

### Database Location
By default, the database is created at `server/database/harmony_installer.db`

### Upload Directory
Files are uploaded to `server/uploads/apps/` by default

### Custom Configuration
You can modify the database path in `database/database.py`:

```python
db = Database("/path/to/your/database.db")
```

## API Examples

### Create Application
```bash
curl -X POST http://localhost:5000/api/apps \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "description": "Test application",
    "bundle_name": "com.example.app",
    "main_ability": "MainAbility",
    "current_version": "1.0.0"
  }'
```

### Create Version
```bash
curl -X POST http://localhost:5000/api/apps/1/versions \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.0.0",
    "description": "First release",
    "release_date": "2024-01-01",
    "size": 1048576,
    "deploy_path": "/data/local/tmp"
  }'
```

### Upload File
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@debug.hap" \
  -F "version_id=1" \
  -F "file_type=hap"
```

## Development

### Project Structure
```
server/
|-- app_db.py              # Main application
|-- database/
|   |-- __init__.py
|   |-- database.py        # Database connection and setup
|   |-- models.py          # Data models
|   `-- migrations.py      # Migration utilities
|-- api/
|   |-- __init__.py
|   |-- apps.py            # Applications API
|   |-- versions.py        # Versions API
|   `-- files.py           # Files API
|-- uploads/               # File storage
|-- database/              # Database files
|-- admin.html             # Admin panel
|-- migrate.py             # Migration script
`-- requirements_db.txt    # Dependencies
```

### Adding New Features

1. **Database Changes**: Update models in `database/models.py`
2. **API Endpoints**: Add routes in appropriate `api/*.py` files
3. **Admin Panel**: Update `admin.html` for UI changes

## Backup and Recovery

### Backup Database
```bash
cp server/database/harmony_installer.db backup/harmony_installer_$(date +%Y%m%d).db
```

### Backup Files
```bash
tar -czf backup/uploads_$(date +%Y%m%d).tar.gz server/uploads/
```

### Recovery
1. Restore database file
2. Restore uploads directory
3. Restart server

## Troubleshooting

### Database Locked
If you get "database is locked" errors:
1. Stop the server
2. Check for existing connections
3. Restart the server

### File Upload Issues
1. Check upload directory permissions
2. Verify file size limits
3. Check disk space

### Migration Errors
1. Backup existing data
2. Check JSON file format
3. Verify file paths exist

## Performance Considerations

- **Database Indexing**: Primary keys and foreign keys are automatically indexed
- **File Storage**: Consider using cloud storage for large deployments
- **Caching**: Implement Redis caching for frequently accessed data
- **Connection Pooling**: SQLite handles connections efficiently

## Security

- **File Upload**: Files are validated and stored securely
- **SQL Injection**: Parameterized queries prevent SQL injection
- **Input Validation**: All inputs are validated before processing
- **File Access**: Files are served through secure endpoints

## License

This project is licensed under the same terms as the original HarmonyOS Installer.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Create an issue in the repository
