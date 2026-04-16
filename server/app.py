from flask import Flask, jsonify, request, g
from database.database import db
from api.apps import init_apps_routes
from api.versions import init_versions_routes
from api.files import init_files_routes
from api.auth import init_auth_routes, validate_api_key, hash_api_key
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
    def _require_api_key_for_endpoints():
        # Skip health check and public endpoints
        if request.path in ('/health', '/', '/admin'):
            return None
        
        # Skip admin management endpoints (they have their own auth)
        if request.path.startswith('/api/admin/'):
            return None
        
        # Check if this endpoint requires API key
        protected = False
        
        # Read operations that need company isolation
        if request.method == 'GET' and (
            request.path == '/api/apps' or 
            request.path.startswith('/api/apps/')
        ):
            protected = True
        
        # Write operations
        if request.method == 'POST' and (
            request.path == '/api/apps' or
            request.path.startswith('/api/apps/') or
            request.path == '/api/versions/create-with-files' or 
            request.path == '/api/upload'
        ):
            protected = True
        elif request.method == 'PUT' and (
            request.path.startswith('/api/apps/') or 
            request.path.startswith('/api/versions/')
        ):
            protected = True
        elif request.method == 'DELETE' and request.path.startswith('/api/'):
            protected = True

        if not protected:
            return None

        # Validate authentication - try X-API-Key first, then JWT token
        provided_key = request.headers.get('X-API-Key')
        
        # Try company API key first
        if provided_key:
            is_valid, company_id, error = validate_api_key(provided_key)
            if is_valid:
                g.company_id = company_id
                return None
        
        # Fall back to admin API key for backward compatibility
        if admin_api_key and provided_key == admin_api_key:
            # For admin key, company_id will be None (access all)
            g.company_id = None
            return None
        
        # Try JWT token as fallback
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            from api.auth import verify_token
            payload, error = verify_token(token)
            if payload:
                # JWT valid - set company_id from token (None for admin, specific ID for company_admin)
                g.company_id = payload.get('company_id')
                g.user = payload  # Store user info for potential use
                return None
        
        # If we get here, authentication failed
        return jsonify({'error': 'Unauthorized - Valid X-API-Key or JWT token required'}), 401

    # Initialize database
    db.ensure_database_exists()
    
    # Initialize auth routes
    init_auth_routes(app)

    # Initialize API routes
    init_apps_routes(app)
    init_versions_routes(app)
    init_files_routes(app)

    @app.route('/health')
    def health_check():
        """Health check endpoint with user-aware statistics"""
        try:
            # Check for JWT authentication
            user = None
            token = None
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            if not token:
                token = request.cookies.get('auth_token')
            
            if token:
                # Import here to avoid circular dependency
                from api.auth import verify_token
                payload, error = verify_token(token)
                if payload:
                    user = payload
            
            with db.get_connection() as conn:
                # Build queries based on user role
                if user and user.get('role') == 'admin' and user.get('company_id') is None:
                    # Admin - count all
                    cursor = conn.execute("SELECT COUNT(*) FROM apps")
                    app_count = cursor.fetchone()[0]

                    cursor = conn.execute("SELECT COUNT(*) FROM versions")
                    version_count = cursor.fetchone()[0]

                    cursor = conn.execute("SELECT COUNT(*) FROM files")
                    file_count = cursor.fetchone()[0]
                elif user and user.get('company_id'):
                    # Company admin - count only their company's data
                    company_id = user.get('company_id')
                    
                    cursor = conn.execute("SELECT COUNT(*) FROM apps WHERE company_id = ?", (company_id,))
                    app_count = cursor.fetchone()[0]

                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM versions v
                        JOIN apps a ON v.app_id = a.id
                        WHERE a.company_id = ?
                    """, (company_id,))
                    version_count = cursor.fetchone()[0]

                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM files f
                        JOIN versions v ON f.version_id = v.id
                        JOIN apps a ON v.app_id = a.id
                        WHERE a.company_id = ?
                    """, (company_id,))
                    file_count = cursor.fetchone()[0]
                else:
                    # No JWT or unknown role - count all (backward compatible)
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
                    'files': file_count,
                    'user_role': user.get('role') if user else None,
                    'company_id': user.get('company_id') if user else None
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
            'version': '3.0.0',
            'description': 'API for managing HarmonyOS applications and versions (SaaS Multi-tenant)',
            'endpoints': {
                'apps': {
                    'GET /api/apps': 'Get all apps for your company',
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
                    'X-API-Key': 'Required for all protected endpoints. Format: X-API-Key: <your_api_key>',
                    'note': 'Each company has isolated data. Use admin endpoints to manage companies and API keys.'
                },
                'admin': {
                    'GET /api/admin/companies': 'List all companies (admin only)',
                    'POST /api/admin/companies': 'Create company with API key (admin only)',
                    'GET /api/admin/companies/{id}/api-keys': 'List company API keys (admin only)',
                    'POST /api/admin/companies/{id}/api-keys': 'Create API key for company (admin only)',
                    'DELETE /api/admin/api-keys/{id}': 'Revoke API key (admin only)',
                    'POST /api/admin/api-keys/{id}/toggle': 'Toggle API key active status (admin only)'
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
