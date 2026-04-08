from flask import Flask, jsonify, send_from_directory
from database.database import db
from api.apps import init_apps_routes
from api.versions import init_versions_routes
from api.files import init_files_routes
import os

def create_app():
    app = Flask(__name__)
    
    # Initialize database
    db.ensure_database_exists()
    
    # Initialize API routes
    init_apps_routes(app)
    init_versions_routes(app)
    init_files_routes(app)
    
    # File serving
    @app.route('/files/<path:filename>')
    def serve_file(filename):
        """Serve uploaded files"""
        try:
            # Find file in database
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT file_path FROM files WHERE filename = ?
                """, (filename,))
                file_record = cursor.fetchone()
                
                if not file_record:
                    return jsonify({'error': 'File not found'}), 404
                
                file_path = file_record['file_path']
                directory = os.path.dirname(file_path)
                return send_from_directory(directory, filename)
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM apps")
                app_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM versions")
                version_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM files")
                file_count = cursor.fetchone()[0]
                
                return jsonify({
                    'status': 'healthy',
                    'database': 'connected',
                    'apps': app_count,
                    'versions': version_count,
                    'files': file_count
                })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/')
    def index():
        """Index page with API documentation"""
        return jsonify({
            'name': 'HarmonyOS Installer API',
            'version': '2.0.0',
            'description': 'API for managing HarmonyOS applications and versions',
            'endpoints': {
                'apps': {
                    'GET /api/apps': 'Get all apps',
                    'POST /api/apps': 'Create new app',
                    'PUT /api/apps/{id}': 'Update app',
                    'DELETE /api/apps/{id}': 'Delete app'
                },
                'versions': {
                    'GET /api/apps/{app_id}/versions': 'Get app versions',
                    'POST /api/apps/{app_id}/versions': 'Create version',
                    'PUT /api/versions/{id}': 'Update version',
                    'DELETE /api/versions/{id}': 'Delete version'
                },
                'files': {
                    'POST /api/upload': 'Upload file',
                    'GET /api/files/{id}': 'Download file',
                    'DELETE /api/files/{id}': 'Delete file'
                }
            }
        })
    
    @app.route('/admin')
    def admin_panel():
        """Admin panel"""
        try:
            with open(os.path.join(os.path.dirname(__file__), 'admin.html'), 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return jsonify({'error': 'Admin panel not found'}), 404
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
