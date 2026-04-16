import sqlite3
import os
from typing import Optional

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'harmony_installer.db')
        
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Ensure database and tables exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    code VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    key_hash VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(100),
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS apps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    bundle_name VARCHAR(255) NOT NULL,
                    main_ability VARCHAR(255) NOT NULL,
                    current_version VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    version_no INTEGER,
                    description TEXT,
                    release_date DATE,
                    deploy_path VARCHAR(500) DEFAULT '/data/local/tmp',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE
                );
                
                -- Create indexes for performance
                CREATE INDEX IF NOT EXISTS idx_apps_company_id ON apps(company_id);
                CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
                CREATE INDEX IF NOT EXISTS idx_api_keys_company_id ON api_keys(company_id);
                
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id INTEGER NOT NULL,
                    file_type VARCHAR(20) NOT NULL CHECK (file_type IN ('hap', 'hsp')),
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size INTEGER,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version_id) REFERENCES versions(id) ON DELETE CASCADE
                );
            """)
            conn.commit()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def migrate_from_json(self, apps_json_path: str, versions_dir: str):
        """Migrate data from JSON files to database"""
        import json
        
        with open(apps_json_path, 'r', encoding='utf-8') as f:
            apps_data = json.load(f)
        
        with self.get_connection() as conn:
            for app in apps_data.get('apps', []):
                # Insert app
                cursor = conn.execute("""
                    INSERT INTO apps (name, description, bundle_name, main_ability, current_version)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    app.get('name'),
                    app.get('description'),
                    app.get('bundle_name'),
                    app.get('main_ability'),
                    app.get('current_version')
                ))
                app_id = cursor.lastrowid
                
                # Migrate versions if they exist
                app_versions_dir = os.path.join(versions_dir, app.get('versions_dir', '').replace('versions/', ''))
                if os.path.exists(app_versions_dir):
                    for version_name in os.listdir(app_versions_dir):
                        version_dir = os.path.join(app_versions_dir, version_name)
                        version_info_file = os.path.join(version_dir, 'version_info.json')
                        
                        if os.path.exists(version_info_file):
                            with open(version_info_file, 'r', encoding='utf-8') as vf:
                                version_info = json.load(vf)
                            
                            # Insert version
                            cursor = conn.execute("""
                                INSERT INTO versions (app_id, version, version_no, description, release_date, deploy_path)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                app_id,
                                version_info.get('version'),
                                version_info.get('version_no'),
                                version_info.get('description'),
                                version_info.get('release_date'),
                                version_info.get('deploy_path', '/data/local/tmp')
                            ))
                            version_id = cursor.lastrowid
                            
                            # Create file records
                            files_dir = os.path.join(version_dir, 'files')
                            if os.path.exists(files_dir):
                                for file_type, filename in version_info.get('files', {}).items():
                                    if filename:
                                        file_path = os.path.join(files_dir, filename)
                                        if os.path.exists(file_path):
                                            file_size = os.path.getsize(file_path)
                                            conn.execute("""
                                                INSERT INTO files (version_id, file_type, filename, file_path, file_size)
                                                VALUES (?, ?, ?, ?, ?)
                                            """, (version_id, file_type, filename, file_path, file_size))
            
            conn.commit()

# Global database instance
db = Database()
