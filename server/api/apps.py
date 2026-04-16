from flask import request, jsonify, g
from database.database import db
from database.models import App


def _get_company_id():
    """Get company_id from request context (set by auth middleware)"""
    return getattr(g, 'company_id', None)


def _verify_app_ownership(conn, app_id, company_id):
    """Verify app belongs to company, returns app data or None"""
    if company_id is None:
        # Admin access - no filtering
        cursor = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
    else:
        cursor = conn.execute(
            "SELECT * FROM apps WHERE id = ? AND company_id = ?",
            (app_id, company_id)
        )
    return cursor.fetchone()

def init_apps_routes(app):
    
    @app.route('/api/apps', methods=['GET'])
    def get_apps():
        """Get all apps for current company"""
        try:
            company_id = _get_company_id()
            
            # Allow admin to filter by specific company via query parameter
            filter_company_id = request.args.get('company_id', type=int)
            
            with db.get_connection() as conn:
                if company_id is None:
                    # Admin access - return all apps or filter by company_id if provided
                    if filter_company_id:
                        cursor = conn.execute(
                            "SELECT * FROM apps WHERE company_id = ? ORDER BY name",
                            (filter_company_id,)
                        )
                    else:
                        cursor = conn.execute("SELECT * FROM apps ORDER BY name")
                else:
                    # Company access - return only their apps
                    cursor = conn.execute(
                        "SELECT * FROM apps WHERE company_id = ? ORDER BY name",
                        (company_id,)
                    )
                
                apps = []
                for row in cursor.fetchall():
                    app_data = dict(row)
                    apps.append(app_data)
                
                return jsonify({'apps': apps})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/apps', methods=['POST'])
    def create_app():
        """Create new app"""
        try:
            data = request.get_json()
            company_id = _get_company_id()
            
            # If admin (company_id is None) and company_id specified in request, use it
            if company_id is None and 'company_id' in data:
                company_id = data['company_id']
            
            # Validate required fields
            required_fields = ['name', 'bundle_name', 'main_ability']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO apps (company_id, name, description, bundle_name, main_ability, current_version)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    company_id,  # Can be None for admin-created apps
                    data.get('name'),
                    data.get('description', ''),
                    data.get('bundle_name'),
                    data.get('main_ability'),
                    data.get('current_version')
                ))
                app_id = cursor.lastrowid
                conn.commit()
                
                # Return created app
                cursor = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
                app = dict(cursor.fetchone())
                
                return jsonify(app), 201
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/apps/<int:app_id>', methods=['PUT'])
    def update_app(app_id):
        """Update app"""
        try:
            data = request.get_json()
            company_id = _get_company_id()
            
            with db.get_connection() as conn:
                # Check if app exists and belongs to company
                app = _verify_app_ownership(conn, app_id, company_id)
                if not app:
                    return jsonify({'error': 'App not found or access denied'}), 404
                
                # Update app
                cursor = conn.execute("""
                    UPDATE apps 
                    SET name = ?, description = ?, bundle_name = ?, main_ability = ?, current_version = ?
                    WHERE id = ?
                """, (
                    data.get('name'),
                    data.get('description'),
                    data.get('bundle_name'),
                    data.get('main_ability'),
                    data.get('current_version'),
                    app_id
                ))
                conn.commit()
                
                # Return updated app
                cursor = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
                app = dict(cursor.fetchone())
                
                return jsonify(app)
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/apps/<int:app_id>', methods=['DELETE'])
    def delete_app(app_id):
        """Delete app"""
        try:
            company_id = _get_company_id()
            
            with db.get_connection() as conn:
                # Check if app exists and belongs to company
                app = _verify_app_ownership(conn, app_id, company_id)
                if not app:
                    return jsonify({'error': 'App not found or access denied'}), 404
                
                # Delete app (cascade will delete versions and files)
                conn.execute("DELETE FROM apps WHERE id = ?", (app_id,))
                conn.commit()
                
                return jsonify({'message': 'App deleted successfully'})
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
