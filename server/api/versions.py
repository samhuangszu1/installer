from flask import request, jsonify
from database.database import db
import os

def init_versions_routes(app):
    
    @app.route('/api/apps/<int:app_id>/versions', methods=['GET'])
    def get_app_versions(app_id):
        """Get all versions for an app"""
        try:
            with db.get_connection() as conn:
                # Check if app exists
                cursor = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
                if not cursor.fetchone():
                    return jsonify({'error': 'App not found'}), 404
                
                # Get versions
                cursor = conn.execute("""
                    SELECT * FROM versions 
                    WHERE app_id = ? 
                    ORDER BY version DESC
                """, (app_id,))
                versions = []
                for row in cursor.fetchall():
                    version_data = dict(row)
                    
                    # Get files for this version
                    files_cursor = conn.execute("""
                        SELECT * FROM files WHERE version_id = ?
                    """, (version_data['id'],))
                    version_data['files'] = [dict(f) for f in files_cursor.fetchall()]
                    
                    versions.append(version_data)
                
                return jsonify({'versions': versions})
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/apps/<int:app_id>/versions', methods=['POST'])
    def create_version(app_id):
        """Create new version for an app"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if 'version' not in data:
                return jsonify({'error': 'Missing required field: version'}), 400
            
            with db.get_connection() as conn:
                # Check if app exists
                cursor = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
                if not cursor.fetchone():
                    return jsonify({'error': 'App not found'}), 404
                
                # Check if version already exists
                cursor = conn.execute("""
                    SELECT * FROM versions WHERE app_id = ? AND version = ?
                """, (app_id, data['version']))
                if cursor.fetchone():
                    return jsonify({'error': 'Version already exists'}), 400
                
                # Create version
                cursor = conn.execute("""
                    INSERT INTO versions (app_id, version, description, release_date, size, 
                                         hap_filename, hsp_filename, deploy_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    app_id,
                    data.get('version'),
                    data.get('description', ''),
                    data.get('release_date'),
                    data.get('size'),
                    data.get('hap_filename'),
                    data.get('hsp_filename'),
                    data.get('deploy_path', '/data/local/tmp')
                ))
                version_id = cursor.lastrowid
                conn.commit()
                
                # Update app's current version if needed
                if data.get('set_as_current', False):
                    conn.execute("""
                        UPDATE apps SET current_version = ? WHERE id = ?
                    """, (data['version'], app_id))
                    conn.commit()
                
                # Return created version
                cursor = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,))
                version = dict(cursor.fetchone())
                
                return jsonify(version), 201
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/versions/<int:version_id>', methods=['PUT'])
    def update_version(version_id):
        """Update version"""
        try:
            data = request.get_json()
            
            with db.get_connection() as conn:
                # Check if version exists
                cursor = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,))
                if not cursor.fetchone():
                    return jsonify({'error': 'Version not found'}), 404
                
                # Update version
                cursor = conn.execute("""
                    UPDATE versions 
                    SET version = ?, description = ?, release_date = ?, size = ?, 
                        hap_filename = ?, hsp_filename = ?, deploy_path = ?
                    WHERE id = ?
                """, (
                    data.get('version'),
                    data.get('description'),
                    data.get('release_date'),
                    data.get('size'),
                    data.get('hap_filename'),
                    data.get('hsp_filename'),
                    data.get('deploy_path'),
                    version_id
                ))
                conn.commit()
                
                # Return updated version
                cursor = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,))
                version = dict(cursor.fetchone())
                
                return jsonify(version)
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/versions/<int:version_id>', methods=['DELETE'])
    def delete_version(version_id):
        """Delete version"""
        try:
            with db.get_connection() as conn:
                # Check if version exists
                cursor = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,))
                if not cursor.fetchone():
                    return jsonify({'error': 'Version not found'}), 404
                
                # Delete version (cascade will delete files)
                conn.execute("DELETE FROM versions WHERE id = ?", (version_id,))
                conn.commit()
                
                return jsonify({'message': 'Version deleted successfully'})
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/versions/<int:version_id>/info', methods=['GET'])
    def get_version_info(version_id):
        """Get version info in the old format for compatibility"""
        try:
            with db.get_connection() as conn:
                # Get version
                cursor = conn.execute("""
                    SELECT v.*, a.bundle_name, a.main_ability 
                    FROM versions v
                    JOIN apps a ON v.app_id = a.id
                    WHERE v.id = ?
                """, (version_id,))
                version = cursor.fetchone()
                
                if not version:
                    return jsonify({'error': 'Version not found'}), 404
                
                # Get files
                cursor = conn.execute("""
                    SELECT file_type, filename FROM files WHERE version_id = ?
                """, (version_id,))
                files = {row['file_type']: row['filename'] for row in cursor.fetchall()}
                
                # Return in old format for compatibility
                version_info = {
                    'version': version['version'],
                    'description': version['description'],
                    'release_date': version['release_date'],
                    'size': version['size'],
                    'deploy_path': version['deploy_path'],
                    'files': files,
                    'bundle_name': version['bundle_name'],
                    'main_ability': version['main_ability']
                }
                
                return jsonify(version_info)
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
