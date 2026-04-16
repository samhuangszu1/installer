"""
Authentication module for API key management and validation
Supports multi-tenant SaaS with company isolation
"""
import hashlib
import secrets
import datetime
import os
from functools import wraps
from flask import request, jsonify, g
from database.database import db
import jwt
from werkzeug.security import generate_password_hash, check_password_hash


# JWT Configuration (module level for shared access)
JWT_SECRET = os.environ.get('JWT_SECRET_KEY') or secrets.token_hex(32)
JWT_EXPIRATION_HOURS = 24


def generate_token(user_id, email, role, company_id=None):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'company_id': company_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_token(token):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, 'Token has expired'
    except jwt.InvalidTokenError:
        return None, 'Invalid token'


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
        
        # First try JWT authentication
        user = None
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            token = request.cookies.get('auth_token')
        
        if token:
            payload, error = verify_token(token)
            if payload:
                user = payload
        
        # If JWT auth successful
        if user:
            is_admin = user.get('role') == 'admin' and user.get('company_id') is None
            with db.get_connection() as conn:
                if is_admin:
                    cursor = conn.execute(
                        "SELECT id, name, code, description, created_at, updated_at FROM companies ORDER BY created_at DESC"
                    )
                    companies = [dict(row) for row in cursor.fetchall()]
                    return jsonify({'companies': companies, 'is_admin': True})
                else:
                    # Company admin - return only their company
                    company_id = user.get('company_id')
                    if company_id:
                        cursor = conn.execute(
                            "SELECT id, name, code, description, created_at, updated_at FROM companies WHERE id = ?",
                            (company_id,)
                        )
                        company = cursor.fetchone()
                        if company:
                            return jsonify({'companies': [dict(company)], 'is_admin': False})
                    return jsonify({'companies': [], 'is_admin': False})
        
        # Fall back to API key authentication
        provided_key = request.headers.get('X-API-Key') 
        if not provided_key:
            return jsonify({'error': 'Unauthorized - API Key or Login required'}), 401
        
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

    # ==================== JWT Authentication for Admin Panel ====================
    
    # Note: generate_token, verify_token, JWT_SECRET are defined at module level
    
    def require_auth(f):
        """Decorator to require JWT authentication"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            # Check for token in header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            # Also check for token in cookie
            if not token:
                token = request.cookies.get('auth_token')
            
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            
            payload, error = verify_token(token)
            if error:
                return jsonify({'error': error}), 401
            
            # Set user info in g
            g.user_id = payload.get('user_id')
            g.user_email = payload.get('email')
            g.user_role = payload.get('role')
            g.user_company_id = payload.get('company_id')
            
            return f(*args, **kwargs)
        return decorated
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Login with email and password, return JWT token"""
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        email = data.get('email').lower().strip()
        password = data.get('password')
        
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, email, password_hash, name, role, company_id, is_active FROM users WHERE email = ?",
                (email,)
            )
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': 'Invalid email or password'}), 401
            
            if not user['is_active']:
                return jsonify({'error': 'Account is deactivated'}), 401
            
            # Verify password
            if not check_password_hash(user['password_hash'], password):
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Check login type and user role match
            login_type = data.get('login_type', 'admin')
            is_admin = user['role'] == 'admin' and user['company_id'] is None
            
            if login_type == 'admin' and not is_admin:
                return jsonify({'error': '不是 admin 账号，请切换到「公司管理员」登录'}), 401
            
            if login_type == 'company' and is_admin:
                return jsonify({'error': '不是公司管理员账号，请切换到「Admin」登录'}), 401
            
            # For company admin, verify API Key
            if not is_admin:
                # Company manager must provide valid API Key
                provided_api_key = request.headers.get('X-API-Key')
                if not provided_api_key:
                    return jsonify({'error': 'API Key required for company manager login'}), 401
                
                # Verify API Key belongs to the user's company
                key_hash = hash_api_key(provided_api_key)
                cursor = conn.execute(
                    """SELECT id, company_id, expires_at, is_active FROM api_keys 
                       WHERE key_hash = ? AND company_id = ?""",
                    (key_hash, user['company_id'])
                )
                api_key_row = cursor.fetchone()
                
                if not api_key_row:
                    return jsonify({'error': 'Invalid API Key - Key does not belong to your company'}), 401
                
                if not api_key_row['is_active']:
                    return jsonify({'error': 'API Key is deactivated - Contact admin'}), 401
                
                # Check expiration
                if api_key_row['expires_at']:
                    expires_at_str = api_key_row['expires_at']
                    # Parse and ensure offset-aware
                    if expires_at_str.endswith('Z'):
                        expires_at_str = expires_at_str[:-1] + '+00:00'
                    expires_at = datetime.datetime.fromisoformat(expires_at_str)
                    # Make offset-aware if not already
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if expires_at < now:
                        return jsonify({'error': 'API Key has expired - Contact admin to renew'}), 401
            
            # Update last login
            conn.execute(
                "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],)
            )
            conn.commit()
            
            # Generate token
            token = generate_token(
                user_id=user['id'],
                email=user['email'],
                role=user['role'],
                company_id=user['company_id']
            )
            
            # Get API key based on user role
            api_key = None
            is_admin = user['role'] == 'admin' and user['company_id'] is None
            
            if is_admin:
                # Return admin API key
                api_key = os.environ.get('ADMIN_API_KEY')
            else:
                # For company user, find their company's API key
                cursor = conn.execute(
                    """SELECT key_hash FROM api_keys 
                       WHERE company_id = ? AND is_active = 1 
                       ORDER BY created_at DESC LIMIT 1""",
                    (user['company_id'],)
                )
                key_row = cursor.fetchone()
                # Note: we can't return the original API key since we only store hash
                # The user needs to use their existing API key or get one from admin
                api_key = None  # Company users need to manually set their API key
            
            return jsonify({
                'token': token,
                'api_key': api_key,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'company_id': user['company_id']
                }
            })
    
    @app.route('/api/auth/logout', methods=['POST'])
    def logout():
        """Logout - client should clear token"""
        # JWT is stateless, just return success
        # Client needs to remove token from storage
        return jsonify({'message': 'Logged out successfully'})
    
    @app.route('/api/auth/me', methods=['GET'])
    @require_auth
    def get_current_user():
        """Get current authenticated user info"""
        return jsonify({
            'user': {
                'id': g.user_id,
                'email': g.user_email,
                'role': g.user_role,
                'company_id': g.user_company_id
            }
        })
    
    @app.route('/api/auth/setup', methods=['POST'])
    def setup_admin():
        """Create initial admin user - can only be used when no users exist"""
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        # Check if admin API key is provided for security
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or provided_key != admin_api_key:
            return jsonify({'error': 'Unauthorized - Valid Admin API Key required'}), 401
        
        with db.get_connection() as conn:
            # Check if any users exist
            cursor = conn.execute("SELECT COUNT(*) as count FROM users")
            if cursor.fetchone()['count'] > 0:
                return jsonify({'error': 'Setup already completed. Use admin panel to create users.'}), 400
            
            email = data.get('email').lower().strip()
            password = data.get('password')
            name = data.get('name', 'Admin')
            
            # Validate password strength
            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            
            # Create admin user
            password_hash = generate_password_hash(password)
            cursor = conn.execute(
                """INSERT INTO users (email, password_hash, name, role, company_id, is_active)
                   VALUES (?, ?, ?, 'admin', NULL, 1)""",
                (email, password_hash, name)
            )
            user_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                'message': 'Admin user created successfully',
                'user': {
                    'id': user_id,
                    'email': email,
                    'name': name,
                    'role': 'admin'
                }
            }), 201
    
    @app.route('/api/admin/companies/<int:company_id>/managers', methods=['POST'])
    def create_company_manager(company_id):
        """Create a company manager user (admin only)"""
        # Check if admin API key is provided for security
        admin_api_key = os.environ.get('ADMIN_API_KEY')
        provided_key = request.headers.get('X-API-Key')
        
        # Also check JWT auth
        user = None
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            token = request.cookies.get('auth_token')
        if token:
            payload, error = verify_token(token)
            if payload:
                user = payload
        
        is_admin = False
        if user and user.get('role') == 'admin' and user.get('company_id') is None:
            is_admin = True
        elif provided_key and provided_key == admin_api_key:
            is_admin = True
        
        if not is_admin:
            return jsonify({'error': 'Unauthorized - Admin access required'}), 401
        
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        email = data.get('email').lower().strip()
        password = data.get('password')
        name = data.get('name', 'Company Manager')
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        with db.get_connection() as conn:
            # Check if company exists
            cursor = conn.execute("SELECT id, name FROM companies WHERE id = ?", (company_id,))
            company = cursor.fetchone()
            if not company:
                return jsonify({'error': 'Company not found'}), 404
            
            # Check if email already exists
            cursor = conn.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 400
            
            # Create company manager user
            password_hash = generate_password_hash(password)
            cursor = conn.execute(
                """INSERT INTO users (email, password_hash, name, role, company_id, is_active)
                   VALUES (?, ?, ?, 'company_admin', ?, 1)""",
                (email, password_hash, name, company_id)
            )
            user_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                'message': 'Company manager created successfully',
                'user': {
                    'id': user_id,
                    'email': email,
                    'name': name,
                    'role': 'company_admin',
                    'company_id': company_id,
                    'company_name': company['name']
                }
            }), 201
