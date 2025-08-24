# UserMS/app.py
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import uuid
import redis
from functools import wraps
import logging
import os
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('mysql.connector').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Configuration class
class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'user-auth-secret-key-change-in-production')
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Database Configuration
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_NAME = os.environ.get('DB_NAME', 'levels_living_db')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    
    # Redis Configuration
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # Service Configuration
    SERVICE_NAME = 'user-auth-service'
    SERVICE_PORT = int(os.environ.get('SERVICE_PORT', 5001))
    
    # Security Configuration
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    ACCOUNT_LOCKOUT_DURATION = int(os.environ.get('ACCOUNT_LOCKOUT_DURATION', 30))  # minutes

app = Flask(__name__)
app.config.from_object(Config)

# Initialize JWT
jwt = JWTManager(app)

# Initialize Redis for session management
try:
    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test Redis connection
    redis_client.ping()
    logger.info("Redis connected successfully")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

class DatabaseManager:
    def __init__(self):
        self.host = Config.DB_HOST
        self.database = Config.DB_NAME
        self.user = Config.DB_USER
        self.password = Config.DB_PASSWORD
        self.port = Config.DB_PORT
    
    def get_connection(self):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                autocommit=True,
                connection_timeout=10
            )
            return connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def execute_query(self, query, params=None, fetch=False):
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall() if fetch == 'all' else cursor.fetchone()
            else:
                result = cursor.rowcount
            
            return result
        except Error as e:
            logger.error(f"Query execution error: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

db = DatabaseManager()

class UserService:
    @staticmethod
    def create_user(email, password, role):
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = db.execute_query(
                "SELECT user_id FROM users WHERE email = %s",
                (email,),
                fetch='one'
            )
            
            if existing_user:
                return {"error": "User already exists"}, 409
            
            # Hash password
            password_hash = generate_password_hash(password)
            user_id = str(uuid.uuid4())
            
            # Insert new user
            result = db.execute_query(
                """INSERT INTO users (user_id, email, password_hash, role) 
                   VALUES (%s, %s, %s, %s)""",
                (user_id, email, password_hash, role)
            )
            
            if result:
                logger.info(f"User created successfully: {email}")
                return {
                    "message": "User created successfully",
                    "user_id": user_id,
                    "email": email,
                    "role": role
                }, 201
            else:
                return {"error": "Failed to create user"}, 500
                
        except Exception as e:
            logger.error(f"Create user error: {e}")
            return {"error": "Internal server error"}, 500
    
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user credentials"""
        try:
            # Get user from database
            user = db.execute_query(
                """SELECT user_id, email, password_hash, role, is_active, 
                          login_attempts, locked_until 
                   FROM users WHERE email = %s""",
                (email,),
                fetch='one'
            )
            
            if not user:
                return {"error": "Invalid credentials"}, 401
            
            # Check if account is locked
            if user['locked_until'] and datetime.now() < user['locked_until']:
                return {"error": "Account is temporarily locked"}, 423
            
            # Check if account is active
            if not user['is_active']:
                return {"error": "Account is deactivated"}, 403
            
            # Verify password
            if not check_password_hash(user['password_hash'], password):
                # Increment failed login attempts
                attempts = user['login_attempts'] + 1
                locked_until = None
                
                if attempts >= Config.MAX_LOGIN_ATTEMPTS:
                    locked_until = datetime.now() + timedelta(minutes=Config.ACCOUNT_LOCKOUT_DURATION)
                
                db.execute_query(
                    """UPDATE users SET login_attempts = %s, locked_until = %s 
                       WHERE user_id = %s""",
                    (attempts, locked_until, user['user_id'])
                )
                
                return {"error": "Invalid credentials"}, 401
            
            # Reset login attempts on successful login
            db.execute_query(
                """UPDATE users SET login_attempts = 0, locked_until = NULL, 
                          last_login = NOW() WHERE user_id = %s""",
                (user['user_id'],)
            )
            
            logger.info(f"User authenticated successfully: {email}")
            return user, 200
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {"error": "Internal server error"}, 500
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        try:
            user = db.execute_query(
                """SELECT user_id, email, role, is_active, last_login, created_at 
                   FROM users WHERE user_id = %s""",
                (user_id,),
                fetch='one'
            )
            
            if user:
                return user, 200
            else:
                return {"error": "User not found"}, 404
                
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return {"error": "Internal server error"}, 500

class SessionService:
    @staticmethod
    def create_session(user_id, refresh_token, user_agent=None, ip_address=None):
        """Create a new user session"""
        try:
            session_id = str(uuid.uuid4())
            refresh_token_hash = generate_password_hash(refresh_token)
            expires_at = datetime.now() + timedelta(days=7)  # 7 days expiry
            
            result = db.execute_query(
                """INSERT INTO user_sessions 
                   (session_id, user_id, refresh_token_hash, expires_at, user_agent, ip_address)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (session_id, user_id, refresh_token_hash, expires_at, user_agent, ip_address)
            )
            
            if result:
                return session_id, 201
            else:
                return None, 500
                
        except Exception as e:
            logger.error(f"Create session error: {e}")
            return None, 500

# JWT token blacklist using Redis
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    if not redis_client:
        return False
    
    try:
        jti = jwt_payload['jti']
        token_in_redis = redis_client.get(jti)
        return token_in_redis is not None
    except Exception as e:
        logger.error(f"Token blacklist check error: {e}")
        return False

def role_required(allowed_roles):
    """Decorator to check user role"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user, status = UserService.get_user_by_id(current_user_id)
            
            if status != 200:
                return jsonify({"error": "User not found"}), 404
            
            if user['role'] not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Check database connection
    db_status = "connected" if db.get_connection() else "disconnected"
    
    # Check Redis connection
    redis_status = "connected"
    if redis_client:
        try:
            redis_client.ping()
        except:
            redis_status = "disconnected"
    else:
        redis_status = "disconnected"
    
    return jsonify({
        "status": "healthy",
        "service": "user-auth",
        "database": db_status,
        "redis": redis_status
    }), 200

@app.route('/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['email', 'password', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate email format
        email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Validate role
        allowed_roles = ['admin', 'warehouse', 'driver', 'hq', 'customer_service']
        if data['role'] not in allowed_roles:
            return jsonify({"error": f"Invalid role. Must be one of: {', '.join(allowed_roles)}"}), 400
        
        # Validate password strength
        if len(data['password']) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        
        result, status = UserService.create_user(
            data['email'], 
            data['password'], 
            data['role']
        )
        
        return jsonify(result), status
        
    except Exception as e:
        logger.error(f"Register error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400
        
        # Authenticate user
        user, status = UserService.authenticate_user(data['email'], data['password'])
        
        if status != 200:
            return jsonify(user), status
        
        # Create JWT tokens
        access_token = create_access_token(
            identity=user['user_id'],
            additional_claims={'role': user['role'], 'email': user['email']}
        )
        
        refresh_token = create_refresh_token(identity=user['user_id'])
        
        # Create session
        user_agent = request.headers.get('User-Agent')
        ip_address = request.remote_addr
        
        session_id, session_status = SessionService.create_session(
            user['user_id'], 
            refresh_token,
            user_agent, 
            ip_address
        )
        
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id if session_status == 201 else None,
            "user": {
                "user_id": user['user_id'],
                "email": user['email'],
                "role": user['role']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout"""
    try:
        jti = get_jwt()['jti']
        
        # Add JWT to blacklist if Redis is available
        if redis_client:
            try:
                redis_client.set(jti, "revoked", ex=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
            except Exception as e:
                logger.error(f"Redis blacklist error: {e}")
        
        return jsonify({"message": "Logout successful"}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    try:
        current_user_id = get_jwt_identity()
        user, status = UserService.get_user_by_id(current_user_id)
        
        return jsonify(user), status
        
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/auth/validate', methods=['POST'])
@jwt_required()
def validate_token():
    """Validate JWT token"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        
        return jsonify({
            "valid": True,
            "user_id": current_user_id,
            "role": claims.get('role'),
            "email": claims.get('email')
        }), 200
        
    except Exception as e:
        logger.error(f"Validate token error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/auth/users', methods=['GET'])
@role_required(['admin', 'hq'])
def list_users():
    """List all users (admin only)"""
    try:
        users = db.execute_query(
            """SELECT user_id, email, role, is_active, last_login, created_at 
               FROM users ORDER BY created_at DESC""",
            fetch='all'
        )
        
        return jsonify({"users": users or []}), 200
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=Config.SERVICE_PORT)