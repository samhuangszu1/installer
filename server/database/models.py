from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class App:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    bundle_name: str = ""
    main_ability: str = ""
    current_version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'bundle_name': self.bundle_name,
            'main_ability': self.main_ability,
            'current_version': self.current_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

@dataclass
class Version:
    id: Optional[int] = None
    app_id: int = 0
    version: str = ""
    description: str = ""
    release_date: Optional[str] = None
    deploy_path: str = "/data/local/tmp"
    created_at: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'app_id': self.app_id,
            'version': self.version,
            'description': self.description,
            'release_date': self.release_date,
            'deploy_path': self.deploy_path,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class File:
    id: Optional[int] = None
    version_id: int = 0
    file_type: str = ""  # 'hap' or 'hsp'
    filename: str = ""
    file_path: str = ""
    file_size: Optional[int] = None
    upload_time: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'version_id': self.version_id,
            'file_type': self.file_type,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None
        }
