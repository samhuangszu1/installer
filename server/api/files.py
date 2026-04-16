from flask import request, jsonify, send_file, g
from database.database import db
from werkzeug.utils import secure_filename
import os
import uuid


def _get_company_id():
    """Get company_id from request context (set by auth middleware)"""
    return getattr(g, 'company_id', None)


def _verify_version_ownership(conn, version_id, company_id):
    """Verify version belongs to company through its app, returns version data or None"""
    if company_id is None:
        cursor = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,))
    else:
        cursor = conn.execute("""
            SELECT v.* FROM versions v
            JOIN apps a ON v.app_id = a.id
            WHERE v.id = ? AND a.company_id = ?
        """, (version_id, company_id))
    return cursor.fetchone()


def _verify_file_ownership(conn, file_id, company_id):
    """Verify file belongs to company through its version's app, returns file data or None"""
    if company_id is None:
        cursor = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,))
    else:
        cursor = conn.execute("""
            SELECT f.* FROM files f
            JOIN versions v ON f.version_id = v.id
            JOIN apps a ON v.app_id = a.id
            WHERE f.id = ? AND a.company_id = ?
        """, (file_id, company_id))
    return cursor.fetchone()

def init_files_routes(app):
    
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """Upload file"""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            version_id = request.form.get('version_id')
            file_type = request.form.get('file_type')  # 'hap' or 'hsp'
            
            if not version_id or not file_type:
                return jsonify({'error': 'Missing version_id or file_type'}), 400
            
            if file_type not in ['hap', 'hsp']:
                return jsonify({'error': 'Invalid file_type. Must be hap or hsp'}), 400
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            company_id = _get_company_id()
            
            # Check if version exists and belongs to company
            with db.get_connection() as conn:
                version = _verify_version_ownership(conn, version_id, company_id)
                if not version:
                    return jsonify({'error': 'Version not found or access denied'}), 400
                
                # Create upload directory
                upload_dir = os.path.join('uploads', 'apps', str(version['app_id']), version_id)
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Check if file of this type already exists and delete it
                cursor = conn.execute("SELECT filename FROM files WHERE version_id = ? AND file_type = ?", 
                                   (version_id, file_type))
                existing_file = cursor.fetchone()
                
                if existing_file:
                    # Delete old file from disk
                    old_filename = existing_file['filename']
                    old_file_path = os.path.join(upload_dir, old_filename)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                    
                    # Delete old file record
                    conn.execute("DELETE FROM files WHERE version_id = ? AND file_type = ?", 
                               (version_id, file_type))
                
                # Insert new file record
                file_size = os.path.getsize(file_path)
                cursor = conn.execute("""
                    INSERT INTO files (version_id, file_type, filename, file_path, file_size)
                    VALUES (?, ?, ?, ?, ?)
                """, (version_id, file_type, filename, file_path, file_size))
                
                conn.commit()
                
                return jsonify({
                    'message': 'File uploaded successfully',
                    'filename': filename,
                    'file_size': file_size,
                    'file_id': cursor.lastrowid
                })
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/files/<int:file_id>', methods=['GET'])
    def download_file(file_id):
        """Download file"""
        try:
            company_id = _get_company_id()
            
            with db.get_connection() as conn:
                file_record = _verify_file_ownership(conn, file_id, company_id)
                
                if not file_record:
                    return jsonify({'error': 'File not found or access denied'}), 404
                
                if not os.path.exists(file_record['file_path']):
                    return jsonify({'error': 'File not found on disk'}), 404
                
                return send_file(
                    file_record['file_path'],
                    as_attachment=True,
                    download_name=file_record['filename']
                )
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/files/<int:file_id>', methods=['DELETE'])
    def delete_file(file_id):
        """Delete file"""
        try:
            company_id = _get_company_id()
            
            with db.get_connection() as conn:
                file_record = _verify_file_ownership(conn, file_id, company_id)
                
                if not file_record:
                    return jsonify({'error': 'File not found or access denied'}), 404
                
                # Delete file from disk
                if os.path.exists(file_record['file_path']):
                    os.remove(file_record['file_path'])
                
                # Delete from database
                conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
                conn.commit()
                
                return jsonify({'message': 'File deleted successfully'})
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/versions/<int:version_id>/files/<file_type>/download', methods=['GET'])
    def download_version_file(version_id, file_type):
        """Download specific file for a version"""
        try:
            company_id = _get_company_id()
            
            with db.get_connection() as conn:
                # Verify version ownership and get file
                if company_id is None:
                    cursor = conn.execute("""
                        SELECT f.* FROM files f
                        WHERE f.version_id = ? AND f.file_type = ?
                    """, (version_id, file_type))
                else:
                    cursor = conn.execute("""
                        SELECT f.* FROM files f
                        JOIN versions v ON f.version_id = v.id
                        JOIN apps a ON v.app_id = a.id
                        WHERE f.version_id = ? AND f.file_type = ? AND a.company_id = ?
                    """, (version_id, file_type, company_id))
                
                file_record = cursor.fetchone()
                
                if not file_record:
                    return jsonify({'error': 'File not found or access denied'}), 404
                
                if not os.path.exists(file_record['file_path']):
                    return jsonify({'error': 'File not found on disk'}), 404
                
                return send_file(
                    file_record['file_path'],
                    as_attachment=True,
                    download_name=file_record['filename']
                )
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
