from flask import request, jsonify
from database.database import db
from werkzeug.utils import secure_filename
import os
import uuid

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
                        SELECT file_type, filename FROM files WHERE version_id = ?
                    """, (version_data['id'],))
                    
                    files = {}
                    for file_row in files_cursor.fetchall():
                        files[file_row['file_type']] = file_row['filename']
                    
                    version_data['files'] = files
                    
                    versions.append(version_data)
                
                return jsonify({'versions': versions})
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/versions/create-with-files', methods=['POST'])
    def create_version_with_files():
        try:
            app_id = request.form.get('app_id')
            version_number = request.form.get('version')
            description = request.form.get('description', '')
            release_date = request.form.get('release_date')
            deploy_path = request.form.get('deploy_path', '/data/local/tmp')
            set_as_current_raw = request.form.get('set_as_current', 'false')

            hap_file = request.files.get('hap_file')
            hsp_file = request.files.get('hsp_file')

            if not app_id:
                return jsonify({'error': 'Missing required field: app_id'}), 400
            try:
                app_id_int = int(app_id)
            except ValueError:
                return jsonify({'error': 'Invalid app_id'}), 400

            if not version_number:
                return jsonify({'error': 'Missing required field: version'}), 400

            if hap_file is None or hsp_file is None:
                return jsonify({'error': 'Missing required files: hap_file and hsp_file are required'}), 400

            if not hap_file.filename or not hsp_file.filename:
                return jsonify({'error': 'No file selected'}), 400

            hap_name = secure_filename(hap_file.filename)
            hsp_name = secure_filename(hsp_file.filename)

            if not hap_name.lower().endswith('.hap'):
                return jsonify({'error': 'Invalid hap_file extension. Must be .hap'}), 400
            if not hsp_name.lower().endswith('.hsp'):
                return jsonify({'error': 'Invalid hsp_file extension. Must be .hsp'}), 400

            set_as_current = str(set_as_current_raw).strip().lower() in ('1', 'true', 'yes', 'on')

            tmp_root = os.path.join('uploads', 'tmp')
            os.makedirs(tmp_root, exist_ok=True)

            hap_tmp_path = os.path.join(tmp_root, f"{uuid.uuid4().hex}_{hap_name}")
            hsp_tmp_path = os.path.join(tmp_root, f"{uuid.uuid4().hex}_{hsp_name}")

            created_tmp_paths = []
            created_final_paths = []
            cleanup_old_paths = []
            with db.get_connection() as conn:
                try:
                    cursor = conn.execute("SELECT 1 FROM apps WHERE id = ?", (app_id_int,))
                    if not cursor.fetchone():
                        return jsonify({'error': 'App not found'}), 404

                    cursor = conn.execute(
                        "SELECT id FROM versions WHERE app_id = ? AND version = ?",
                        (app_id_int, version_number),
                    )
                    existing = cursor.fetchone()

                    if existing:
                        version_id = int(existing['id'])
                        conn.execute(
                            """
                            UPDATE versions
                            SET description = ?, release_date = ?, deploy_path = ?
                            WHERE id = ?
                            """,
                            (description, release_date, deploy_path, version_id),
                        )
                    else:
                        cursor = conn.execute(
                            """
                            INSERT INTO versions (app_id, version, description, release_date, deploy_path)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (app_id_int, version_number, description, release_date, deploy_path),
                        )
                        version_id = int(cursor.lastrowid)

                    if set_as_current:
                        conn.execute(
                            "UPDATE apps SET current_version = ? WHERE id = ?",
                            (version_number, app_id_int),
                        )

                    hap_file.save(hap_tmp_path)
                    created_tmp_paths.append(hap_tmp_path)
                    hsp_file.save(hsp_tmp_path)
                    created_tmp_paths.append(hsp_tmp_path)

                    for file_type in ('hap', 'hsp'):
                        cursor = conn.execute(
                            "SELECT id, file_path FROM files WHERE version_id = ? AND file_type = ?",
                            (version_id, file_type),
                        )
                        old = cursor.fetchone()
                        if old and old['file_path']:
                            cleanup_old_paths.append(old['file_path'])
                        if old:
                            conn.execute("DELETE FROM files WHERE id = ?", (int(old['id']),))

                    upload_dir = os.path.join('uploads', 'apps', str(app_id_int), str(version_id))
                    os.makedirs(upload_dir, exist_ok=True)

                    hap_final_path = os.path.join(upload_dir, hap_name)
                    hsp_final_path = os.path.join(upload_dir, hsp_name)

                    os.replace(hap_tmp_path, hap_final_path)
                    created_final_paths.append(hap_final_path)
                    created_tmp_paths.remove(hap_tmp_path)

                    os.replace(hsp_tmp_path, hsp_final_path)
                    created_final_paths.append(hsp_final_path)
                    created_tmp_paths.remove(hsp_tmp_path)

                    hap_size = os.path.getsize(hap_final_path)
                    hsp_size = os.path.getsize(hsp_final_path)

                    conn.execute(
                        """
                        INSERT INTO files (version_id, file_type, filename, file_path, file_size)
                        VALUES (?, 'hap', ?, ?, ?)
                        """,
                        (version_id, hap_name, hap_final_path, hap_size),
                    )
                    conn.execute(
                        """
                        INSERT INTO files (version_id, file_type, filename, file_path, file_size)
                        VALUES (?, 'hsp', ?, ?, ?)
                        """,
                        (version_id, hsp_name, hsp_final_path, hsp_size),
                    )

                    conn.commit()

                    for old_path in cleanup_old_paths:
                        try:
                            if old_path in (hap_final_path, hsp_final_path):
                                continue
                            if old_path and os.path.exists(old_path):
                                os.remove(old_path)
                        except Exception:
                            pass

                    cursor = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,))
                    version_row = cursor.fetchone()
                    version_data = dict(version_row) if version_row else {'id': version_id}
                    version_data['files'] = {'hap': hap_name, 'hsp': hsp_name}
                    return jsonify(version_data), 201
                except Exception as e:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                    for p in list(created_final_paths):
                        try:
                            if p and os.path.exists(p):
                                os.remove(p)
                        except Exception:
                            pass

                    for p in list(created_tmp_paths):
                        try:
                            if p and os.path.exists(p):
                                os.remove(p)
                        except Exception:
                            pass

                    return jsonify({'error': str(e)}), 500

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
                
                # Create version
                cursor = conn.execute("""
                    INSERT INTO versions (app_id, version, description, release_date, deploy_path)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    app_id,
                    data.get('version'),
                    data.get('description', ''),
                    data.get('release_date'),
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
                    SET version = ?, description = ?, release_date = ?, deploy_path = ?
                    WHERE id = ?
                """, (
                    data.get('version'),
                    data.get('description'),
                    data.get('release_date'),
                    data.get('deploy_path'),
                    version_id
                ))
                conn.commit()
                
                # Return updated version with files
                cursor = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,))
                version = dict(cursor.fetchone())
                
                # Get files for this version
                files_cursor = conn.execute("""
                    SELECT f.file_type, f.filename FROM files f
                    JOIN versions v ON f.version_id = v.id
                    WHERE v.id = ?
                """, (version_id,))
                
                files = {}
                for file_row in files_cursor.fetchall():
                    files[file_row['file_type']] = file_row['filename']
                
                version['files'] = files
                
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
                    'deploy_path': version['deploy_path'],
                    'files': files,
                    'bundle_name': version['bundle_name'],
                    'main_ability': version['main_ability']
                }
                
                return jsonify(version_info)
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/versions/<int:version_id>/files/<file_type>', methods=['DELETE'])
    def delete_version_file(version_id, file_type):
        """Delete specific file type from a version"""
        try:
            with db.get_connection() as conn:
                # Get version info
                cursor = conn.execute("""
                    SELECT v.*, a.name as app_name, a.bundle_name
                    FROM versions v
                    JOIN apps a ON v.app_id = a.id
                    WHERE v.id = ?
                """, (version_id,))
                version_data = cursor.fetchone()

                if not version_data:
                    return jsonify({'error': 'Version not found'}), 404

                # Get file info before deletion
                cursor = conn.execute("SELECT filename FROM files WHERE version_id = ? AND file_type = ?", 
                                   (version_id, file_type))
                file_info = cursor.fetchone()
                
                if not file_info:
                    return jsonify({'error': 'File not found'}), 404

                # Delete file from disk
                upload_dir = os.path.join('uploads', 'apps', str(version_data['app_id']), str(version_id))
                file_path = os.path.join(upload_dir, file_info['filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)

                # Delete file record
                cursor = conn.execute("DELETE FROM files WHERE version_id = ? AND file_type = ?", 
                                   (version_id, file_type))
                
                conn.commit()

                return jsonify({'message': f'{file_type} file deleted successfully'})

        except Exception as e:
            return jsonify({'error': str(e)}), 500
