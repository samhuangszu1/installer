from flask import Flask, jsonify, request
from database.database import db
from api.apps import init_apps_routes
from api.versions import init_versions_routes
from api.files import init_files_routes
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def create_app():
    app = Flask(__name__)

    admin_api_key = os.environ.get('ADMIN_API_KEY')

    @app.before_request
    def _require_api_key_for_upload_endpoints():
        protected = False

        if request.method == 'POST' and request.path in ('/api/versions/create-with-files', '/api/upload'):
            protected = True
        elif request.method == 'PUT' and (request.path.startswith('/api/apps/') or request.path.startswith('/api/versions/')):
            protected = True
        elif request.method == 'DELETE' and request.path.startswith('/api/'):
            protected = True

        if not protected:
            return None

        if not admin_api_key:
            return None

        provided = request.headers.get('X-API-Key')
        if not provided or provided != admin_api_key:
            return jsonify({'error': 'Unauthorized'}), 401

    # Initialize database
    db.ensure_database_exists()

    # Initialize API routes
    init_apps_routes(app)
    init_versions_routes(app)
    init_files_routes(app)

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
            'version': '2.1.0',
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
                    'POST /api/versions/create-with-files': 'Create or overwrite version and upload HAP/HSP files (multipart)',
                    'PUT /api/versions/{id}': 'Update version',
                    'DELETE /api/versions/{id}': 'Delete version',
                    'GET /api/versions/{id}/info': 'Get version info (compat format)',
                    'DELETE /api/versions/{version_id}/files/{file_type}': 'Delete version file by type (hap/hsp)'
                },
                'files': {
                    'POST /api/upload': 'Upload file',
                    'GET /api/files/{id}': 'Download file',
                    'DELETE /api/files/{id}': 'Delete file',
                    'GET /api/versions/{version_id}/files/{file_type}/download': 'Download specific file for a version (hap/hsp)'
                },
                'auth': {
                    'X-API-Key': 'If ADMIN_API_KEY is set, required for POST /api/versions/create-with-files, POST /api/upload, PUT /api/apps/*, PUT /api/versions/*, DELETE /api/*'
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
