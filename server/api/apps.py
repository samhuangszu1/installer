from flask import request, jsonify
from database.database import db
from database.models import App

def init_apps_routes(app):
    
    @app.route('/api/apps', methods=['GET'])
    def get_apps():
        """Get all apps"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM apps ORDER BY name")
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
            
            # Validate required fields
            required_fields = ['name', 'bundle_name', 'main_ability']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO apps (name, description, bundle_name, main_ability, current_version)
                    VALUES (?, ?, ?, ?, ?)
                """, (
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
            
            with db.get_connection() as conn:
                # Check if app exists
                cursor = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
                if not cursor.fetchone():
                    return jsonify({'error': 'App not found'}), 404
                
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
            with db.get_connection() as conn:
                # Check if app exists
                cursor = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
                if not cursor.fetchone():
                    return jsonify({'error': 'App not found'}), 404
                
                # Delete app (cascade will delete versions and files)
                conn.execute("DELETE FROM apps WHERE id = ?", (app_id,))
                conn.commit()
                
                return jsonify({'message': 'App deleted successfully'})
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
