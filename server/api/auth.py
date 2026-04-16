"""
Authentication module for API key management and validation
Supports multi-tenant SaaS with company isolation
"""
import hashlib
import secrets
import datetime
from functools import wraps
from flask import request, jsonify, g
from database.database import db


def generate_api_key():
    """Generate a new secure API key"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key):
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_api_key(api_key):
    """
    Validate API key and return company_id if valid
    Returns (is_valid, company_id, error_message)
    """
    if not api_key:
        return False, None, 'Missing API key'
    
    key_hash = hash_api_key(api_key)
    
    with db.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT ak.id, ak.company_id, ak.expires_at, ak.is_active, ak.last_used_at
            FROM api_keys ak
            WHERE ak.key_hash = ?
            """,
            (key_hash,)
        )
        key_record = cursor.fetchone()
        
        if not key_record:
            return False, None, 'Invalid API key'
        
        if not key_record['is_active']:
            return False, None, 'API key is deactivated'
        
        # Check expiration
        if key_record['expires_at']:
            expires_str = key_record['expires_at']
            # Parse expires_at and ensure it's offset-aware
            if expires_str.endswith('Z'):
                expires_at = datetime.datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            elif '+' in expires_str or '-' in expires_str[10:]:  # has timezone info
                expires_at = datetime.datetime.fromisoformat(expires_str)
            else:
                # offset-naive, convert to offset-aware UTC
                expires_at = datetime.datetime.fromisoformat(expires_str).replace(tzinfo=datetime.timezone.utc)
            
            now = datetime.datetime.now(datetime.timezone.utc)
            if now > expires_at:
                return False, None, 'API key has expired'
        
        # Update last_used_at
        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
            (datetime.datetime.now().isoformat(), key_record['id'])
        )
        conn.commit()
        
        return True, key_record['company_id'], None


def require_api_key(f):
    """Decorator to require API key for endpoint"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        is_valid, company_id, error = validate_api_key(api_key)
        
        if not is_valid:
            return jsonify({'error': error}), 401
        
        # Store company_id in Flask g object for use in the endpoint
        g.company_id = company_id
        
        return f(*args, **kwargs)
    
    return decorated


def get_company_id():
    """Get current company_id from request context"""
    return getattr(g, 'company_id', None)


def init_auth_routes(app):
    """Initialize authentication management routes (admin only)"""
    
    @app.route('/api/admin/companies', methods=['GET'])
    def list_companies():
        """List companies - admin sees all, company sees only itself"""
        import os
        from datetime import datetime
        
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key:
            return jsonify({'error': 'Unauthorized - API Key required'}), 401
        
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        is_admin = provided_key == admin_api_key
        
        with db.get_connection() as conn:
            # Check if it's admin key
            if is_admin:
                # Admin - return all companies
                cursor = conn.execute(
                    "SELECT id, name, code, description, created_at, updated_at FROM companies ORDER BY created_at DESC"
                )
                companies = [dict(row) for row in cursor.fetchall()]
                return jsonify({'companies': companies, 'is_admin': True})
            
            # Check if it's a valid company API key
            from api.auth import hash_api_key
            key_hash = hash_api_key(provided_key)
            cursor = conn.execute(
                "SELECT company_id, expires_at, is_active FROM api_keys WHERE key_hash = ?",
                (key_hash,)
            )
            key_row = cursor.fetchone()
            
            if not key_row:
                return jsonify({'error': 'Unauthorized - Invalid API Key'}), 401
            
            if not key_row['is_active']:
                return jsonify({'error': 'Unauthorized - API key is deactivated'}), 401
            
            if key_row['expires_at'] and datetime.now().isoformat() > key_row['expires_at']:
                return jsonify({'error': 'Unauthorized - API key has expired'}), 401
            
            # Valid company key - return only their company
            company_id = key_row['company_id']
            cursor = conn.execute(
                "SELECT id, name, code, description, created_at, updated_at FROM companies WHERE id = ?",
                (company_id,)
            )
            company = cursor.fetchone()
            
            if not company:
                return jsonify({'error': 'Company not found'}), 404
            
            return jsonify({'companies': [dict(company)], 'is_admin': False})
    
    @app.route('/api/admin/companies', methods=['POST'])
    def create_company():
        """Create a new company with API key (admin only)"""
        import os
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or provided_key != admin_api_key:
            return jsonify({'error': 'Unauthorized - Admin API Key required'}), 401
        
        data = request.get_json()
        if not data or 'name' not in data or 'code' not in data:
            return jsonify({'error': 'Missing required fields: name, code'}), 400
        
        name = data.get('name')
        code = data.get('code')
        description = data.get('description', '')
        
        # Optional: set expiration for API key (days)
        expires_days = data.get('expires_days')
        if expires_days is not None:
            try:
                expires_days = int(expires_days)
            except (ValueError, TypeError):
                expires_days = None
        
        with db.get_connection() as conn:
            try:
                # Create company
                cursor = conn.execute(
                    "INSERT INTO companies (name, code, description) VALUES (?, ?, ?)",
                    (name, code, description)
                )
                company_id = cursor.lastrowid
                
                # Generate API key
                api_key = generate_api_key()
                key_hash = hash_api_key(api_key)
                
                # Calculate expiration
                expires_at = None
                if expires_days:
                    expires_at = (datetime.datetime.now() + datetime.timedelta(days=expires_days)).isoformat()
                
                # Store API key
                conn.execute(
                    """
                    INSERT INTO api_keys (company_id, key_hash, name, expires_at, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (company_id, key_hash, 'Default Key', expires_at)
                )
                
                conn.commit()
                
                return jsonify({
                    'company': {
                        'id': company_id,
                        'name': name,
                        'code': code,
                        'description': description
                    },
                    'api_key': api_key,  # Only returned once!
                    'expires_at': expires_at
                }), 201
                
            except Exception as e:
                return jsonify({'error': str(e)}), 400
    
    @app.route('/api/admin/companies/<int:company_id>/api-keys', methods=['GET'])
    def list_company_api_keys(company_id):
        """List all API keys for a company - admin sees all, company sees only their own"""
        import os
        from datetime import datetime
        
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key:
            return jsonify({'error': 'Unauthorized - API Key required'}), 401
        
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        is_admin = provided_key == admin_api_key
        
        if not is_admin:
            # Validate company API key and check if it belongs to this company
            key_hash = hash_api_key(provided_key)
            cursor = db.get_connection().execute(
                "SELECT company_id, is_active, expires_at FROM api_keys WHERE key_hash = ?",
                (key_hash,)
            )
            key_row = cursor.fetchone()
            
            if not key_row:
                return jsonify({'error': 'Unauthorized - Invalid API Key'}), 401
            
            if not key_row['is_active']:
                return jsonify({'error': 'Unauthorized - API key is deactivated'}), 401
            
            if key_row['expires_at'] and datetime.now().isoformat() > key_row['expires_at']:
                return jsonify({'error': 'Unauthorized - API key has expired'}), 401
            
            # Company users can only view their own company's keys
            if key_row['company_id'] != company_id:
                return jsonify({'error': 'Unauthorized - Cannot view other company keys'}), 403
        
        with db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, name, expires_at, last_used_at, is_active, created_at
                FROM api_keys
                WHERE company_id = ?
                ORDER BY created_at DESC
                """,
                (company_id,)
            )
            keys = [dict(row) for row in cursor.fetchall()]
            return jsonify({'api_keys': keys})
    
    @app.route('/api/admin/companies/<int:company_id>/api-keys', methods=['POST'])
    def create_api_key(company_id):
        """Create additional API key for company (admin only)"""
        import os
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key or provided_key != admin_api_key:
            return jsonify({'error': 'Unauthorized - Valid Admin API Key required'}), 401
        
        data = request.get_json() or {}
        name = data.get('name', 'New Key')
        expires_days = data.get('expires_days')
        if expires_days is not None:
            try:
                expires_days = int(expires_days)
            except (ValueError, TypeError):
                expires_days = None
        
        with db.get_connection() as conn:
            # Check company exists
            cursor = conn.execute("SELECT id FROM companies WHERE id = ?", (company_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Company not found'}), 404
            
            # Generate API key
            api_key = generate_api_key()
            key_hash = hash_api_key(api_key)
            
            # Calculate expiration
            expires_at = None
            if expires_days:
                expires_at = (datetime.datetime.now() + datetime.timedelta(days=expires_days)).isoformat()
            
            conn.execute(
                """
                INSERT INTO api_keys (company_id, key_hash, name, expires_at, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (company_id, key_hash, name, expires_at)
            )
            conn.commit()
            
            return jsonify({
                'api_key': api_key,  # Only returned once!
                'name': name,
                'expires_at': expires_at
            }), 201
    
    @app.route('/api/admin/api-keys/<int:key_id>', methods=['DELETE'])
    def revoke_api_key(key_id):
        """Revoke an API key (admin only)"""
        import os
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key or provided_key != admin_api_key:
            return jsonify({'error': 'Unauthorized - Valid Admin API Key required'}), 401
        
        with db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            if cursor.rowcount == 0:
                return jsonify({'error': 'API key not found'}), 404
            conn.commit()
            return jsonify({'message': 'API key revoked'})
    
    @app.route('/api/admin/api-keys/<int:key_id>/toggle', methods=['POST'])
    def toggle_api_key(key_id):
        """Activate/Deactivate an API key (admin only)"""
        import os
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key or provided_key != admin_api_key:
            return jsonify({'error': 'Unauthorized - Valid Admin API Key required'}), 401
        
        with db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET is_active = NOT is_active WHERE id = ?",
                (key_id,)
            )
            if cursor.rowcount == 0:
                return jsonify({'error': 'API key not found'}), 404
            conn.commit()
            return jsonify({'message': 'API key status toggled'})
    
    @app.route('/api/admin/companies/<int:company_id>', methods=['DELETE'])
    def delete_company(company_id):
        """Delete a company and all its API keys (admin only)"""
        import os
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key or provided_key != admin_api_key:
            return jsonify({'error': 'Unauthorized - Admin API Key required'}), 401
        
        with db.get_connection() as conn:
            # Check company exists
            cursor = conn.execute("SELECT id FROM companies WHERE id = ?", (company_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Company not found'}), 404
            
            # Delete all API keys for this company
            conn.execute("DELETE FROM api_keys WHERE company_id = ?", (company_id,))
            
            # Delete the company
            conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            
            conn.commit()
            return jsonify({'message': 'Company and all associated API keys deleted'})
    
    @app.route('/api/admin/companies/<int:company_id>', methods=['PUT'])
    def update_company(company_id):
        """Update company basic info (admin only)"""
        import os
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key or provided_key != admin_api_key:
            return jsonify({'error': 'Unauthorized - Admin API Key required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Fields that can be updated
        allowed_fields = ['name', 'code', 'description']
        updates = {}
        for field in allowed_fields:
            if field in data:
                updates[field] = data[field]
        
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        with db.get_connection() as conn:
            # Check company exists
            cursor = conn.execute("SELECT id FROM companies WHERE id = ?", (company_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Company not found'}), 404
            
            # Check code uniqueness if updating code
            if 'code' in updates:
                cursor = conn.execute(
                    "SELECT id FROM companies WHERE code = ? AND id != ?",
                    (updates['code'], company_id)
                )
                if cursor.fetchone():
                    return jsonify({'error': 'Company code already exists'}), 400
            
            # Build update query
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [company_id]
            
            cursor = conn.execute(
                f"UPDATE companies SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            
            return jsonify({'message': 'Company updated successfully'})
