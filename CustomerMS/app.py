# customer_service/app.py
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
import mysql.connector
from mysql.connector import Error
import os
import uuid
import redis
import requests
from datetime import datetime, timedelta
import logging
import re
import json
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('mysql.connector').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Configuration class
class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'customer-service-secret-key'
    
    # JWT Configuration (should match auth service)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access']
    
    # Database Configuration
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_NAME = os.environ.get('DB_NAME') or 'levels_living_db'
    DB_USER = os.environ.get('DB_USER') or 'root'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or ''
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    
    # Redis Configuration
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # Service Configuration
    SERVICE_NAME = 'customer-service'
    SERVICE_PORT = int(os.environ.get('SERVICE_PORT', 5002))
    
    # Auth Service Configuration
    AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL') or 'http://localhost:5001'
    
    # Geocoding Configuration
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY') or ''
    ENABLE_GEOCODING = os.environ.get('ENABLE_GEOCODING', 'false').lower() == 'true'
    
    # Pagination Configuration
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 50))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 100))

app = Flask(__name__)
app.config.from_object(Config)

# Initialize JWT
jwt = JWTManager(app)

# Initialize Redis
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
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
        self.host = os.getenv('DB_HOST', 'localhost')
        self.database = os.getenv('DB_NAME', 'levels_living_db')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.port = int(os.getenv('DB_PORT', 3306))
    
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

# JWT token blacklist check
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
            claims = get_jwt()
            user_role = claims.get('role')
            
            if user_role not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class GeocodeService:
    """Service to handle address geocoding"""
    
    @staticmethod
    def get_coordinates(postal_code, street=None):
        """Get latitude and longitude from address"""
        try:
            # For Singapore postal codes, we can use a simple mapping
            # In production, use Google Geocoding API
            
            # Basic Singapore postal code to coordinate mapping
            postal_mapping = {
                # Central Region
                '238123': (1.3048, 103.8198),  # Orchard
                '179103': (1.2966, 103.8520),  # Marina Bay
                
                # East Region  
                '560123': (1.3701, 103.8454),  # Ang Mo Kio
                '520123': (1.3521, 103.9448),  # Tampines
                
                # West Region
                '259012': (1.3387, 103.7890),  # Bukit Timah
                '640123': (1.3329, 103.7436),  # Jurong
                
                # North Region
                '730123': (1.4491, 103.8198),  # Yishun
                '760123': (1.4304, 103.8318),  # Woodlands
                
                # Default Singapore center
                '000000': (1.3521, 103.8198)
            }
            
            coords = postal_mapping.get(postal_code, postal_mapping['000000'])
            return coords[0], coords[1]  # latitude, longitude
            
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return 1.3521, 103.8198  # Default to Singapore center

class CustomerService:
    @staticmethod
    def create_customer(customer_data):
        """Create a new customer"""
        try:
            # Validate required fields
            required_fields = ['customer_contact', 'customer_postal_code']
            for field in required_fields:
                if field not in customer_data:
                    return {"error": f"Missing required field: {field}"}, 400
            
            # Validate contact number format (Singapore)
            contact_pattern = r'^(\+65)?[689]\d{7}$'
            if not re.match(contact_pattern, customer_data['customer_contact']):
                return {"error": "Invalid Singapore contact number format"}, 400
            
            # Validate postal code (Singapore 6-digit)
            postal_pattern = r'^\d{6}$'
            if not re.match(postal_pattern, customer_data['customer_postal_code']):
                return {"error": "Invalid Singapore postal code format"}, 400
            
            # Check if customer already exists
            existing_customer = db.execute_query(
                "SELECT customer_id FROM customers WHERE customer_contact = %s",
                (customer_data['customer_contact'],),
                fetch='one'
            )
            
            if existing_customer:
                return {"error": "Customer with this contact number already exists"}, 409
            
            # Get coordinates for the address
            latitude, longitude = GeocodeService.get_coordinates(
                customer_data['customer_postal_code'],
                customer_data.get('customer_street')
            )
            
            # Generate customer ID
            customer_id = str(uuid.uuid4())
            
            # Prepare customer data with JSON serialization
            delivery_preferences = json.dumps(customer_data.get('delivery_preferences', {}))
            communication_preferences = json.dumps(customer_data.get('communication_preferences', {"sms": True, "email": False}))
            
            # Insert customer
            query = """
                INSERT INTO customers 
                (customer_id, customer_contact, customer_street, customer_unit, 
                 customer_postal_code, housing_type, latitude, longitude, 
                 delivery_preferences, communication_preferences)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                customer_id,
                customer_data['customer_contact'],
                customer_data.get('customer_street'),
                customer_data.get('customer_unit'),
                customer_data['customer_postal_code'],
                customer_data.get('housing_type'),
                latitude,
                longitude,
                delivery_preferences,
                communication_preferences
            )
            
            result = db.execute_query(query, params)
            
            if result:
                # Return created customer
                created_customer = db.execute_query(
                    "SELECT * FROM customers WHERE customer_id = %s",
                    (customer_id,),
                    fetch='one'
                )
                
                # Parse JSON fields for response
                if created_customer:
                    try:
                        created_customer['delivery_preferences'] = json.loads(created_customer['delivery_preferences'] or '{}')
                        created_customer['communication_preferences'] = json.loads(created_customer['communication_preferences'] or '{}')
                    except:
                        pass
                
                logger.info(f"Customer created successfully: {customer_data['customer_contact']}")
                return {
                    "message": "Customer created successfully",
                    "customer": created_customer
                }, 201
            else:
                return {"error": "Failed to create customer"}, 500
                
        except Exception as e:
            logger.error(f"Create customer error: {e}")
            return {"error": "Internal server error"}, 500
    
    @staticmethod
    def get_customer_by_id(customer_id):
        """Get customer by ID"""
        try:
            customer = db.execute_query(
                "SELECT * FROM customers WHERE customer_id = %s AND is_active = TRUE",
                (customer_id,),
                fetch='one'
            )
            
            if customer:
                # Parse JSON fields
                try:
                    customer['delivery_preferences'] = json.loads(customer['delivery_preferences'] or '{}')
                    customer['communication_preferences'] = json.loads(customer['communication_preferences'] or '{}')
                except:
                    pass
                return customer, 200
            else:
                return {"error": "Customer not found"}, 404
                
        except Exception as e:
            logger.error(f"Get customer error: {e}")
            return {"error": "Internal server error"}, 500
    
    @staticmethod
    def get_customer_by_contact(contact):
        """Get customer by contact number"""
        try:
            customer = db.execute_query(
                "SELECT * FROM customers WHERE customer_contact = %s AND is_active = TRUE",
                (contact,),
                fetch='one'
            )
            
            if customer:
                # Parse JSON fields
                try:
                    customer['delivery_preferences'] = json.loads(customer['delivery_preferences'] or '{}')
                    customer['communication_preferences'] = json.loads(customer['communication_preferences'] or '{}')
                except:
                    pass
                return customer, 200
            else:
                return {"error": "Customer not found"}, 404
                
        except Exception as e:
            logger.error(f"Get customer by contact error: {e}")
            return {"error": "Internal server error"}, 500
    
    @staticmethod
    def search_customers(search_params):
        """Search customers with filters"""
        try:
            # Build dynamic search query
            where_conditions = ["is_active = TRUE"]
            params = []
            
            if search_params.get('postal_code'):
                where_conditions.append("customer_postal_code = %s")
                params.append(search_params['postal_code'])
            
            if search_params.get('housing_type'):
                where_conditions.append("housing_type = %s")
                params.append(search_params['housing_type'])
            
            if search_params.get('contact'):
                where_conditions.append("customer_contact LIKE %s")
                params.append(f"%{search_params['contact']}%")
            
            if search_params.get('street'):
                where_conditions.append("customer_street LIKE %s")
                params.append(f"%{search_params['street']}%")
            
            # Pagination
            limit = min(int(search_params.get('limit', 50)), 100)  # Max 100 results
            offset = int(search_params.get('offset', 0))
            
            query = f"""
                SELECT * FROM customers 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            
            customers = db.execute_query(query, params, fetch='all')
            
            # Parse JSON fields for all customers
            if customers:
                for customer in customers:
                    try:
                        customer['delivery_preferences'] = json.loads(customer['delivery_preferences'] or '{}')
                        customer['communication_preferences'] = json.loads(customer['communication_preferences'] or '{}')
                    except:
                        pass
            
            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(*) as total FROM customers 
                WHERE {' AND '.join(where_conditions)}
            """
            
            count_result = db.execute_query(count_query, params[:-2], fetch='one')
            total_count = count_result['total'] if count_result else 0
            
            return {
                "customers": customers or [],
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_count
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Search customers error: {e}")
            return {"error": "Internal server error"}, 500

class CustomerValidationService:
    @staticmethod
    def validate_customer_data(data, is_update=False):
        """Validate customer data"""
        errors = []
        
        # Required fields for creation
        if not is_update:
            required_fields = ['customer_contact', 'customer_postal_code']
            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append(f"Missing required field: {field}")
        
        # Validate contact number
        if 'customer_contact' in data:
            contact_pattern = r'^(\+65)?[689]\d{7}$'
            if not re.match(contact_pattern, data['customer_contact']):
                errors.append("Invalid Singapore contact number format (+65XXXXXXXX)")
        
        # Validate postal code
        if 'customer_postal_code' in data:
            postal_pattern = r'^\d{6}$'
            if not re.match(postal_pattern, data['customer_postal_code']):
                errors.append("Invalid Singapore postal code format (6 digits)")
        
        # Validate housing type
        if 'housing_type' in data:
            valid_housing_types = ['HDB', 'Condo', 'Landed', 'Commercial']
            if data['housing_type'] not in valid_housing_types:
                errors.append(f"Invalid housing type. Must be one of: {', '.join(valid_housing_types)}")
        
        # Validate preferences format
        if 'delivery_preferences' in data:
            if not isinstance(data['delivery_preferences'], dict):
                errors.append("delivery_preferences must be a JSON object")
        
        if 'communication_preferences' in data:
            if not isinstance(data['communication_preferences'], dict):
                errors.append("communication_preferences must be a JSON object")
        
        return errors

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
        "service": "customer-service",
        "database": db_status,
        "redis": redis_status
    }), 200

@app.route('/customers', methods=['POST'])
@role_required(['admin', 'hq', 'customer_service'])
def create_customer():
    """Create a new customer"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate customer data
        validation_errors = CustomerValidationService.validate_customer_data(data)
        if validation_errors:
            return jsonify({"errors": validation_errors}), 400
        
        result, status = CustomerService.create_customer(data)
        return jsonify(result), status
        
    except Exception as e:
        logger.error(f"Create customer endpoint error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/customers/<customer_id>', methods=['GET'])
@role_required(['admin', 'hq', 'customer_service', 'warehouse', 'driver'])
def get_customer(customer_id):
    """Get customer by ID"""
    try:
        result, status = CustomerService.get_customer_by_id(customer_id)
        return jsonify(result), status
        
    except Exception as e:
        logger.error(f"Get customer endpoint error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/customers/contact/<contact>', methods=['GET'])
@role_required(['admin', 'hq', 'customer_service', 'warehouse', 'driver'])
def get_customer_by_contact(contact):
    """Get customer by contact number"""
    try:
        result, status = CustomerService.get_customer_by_contact(contact)
        return jsonify(result), status
        
    except Exception as e:
        logger.error(f"Get customer by contact endpoint error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/customers', methods=['GET'])
@role_required(['admin', 'hq', 'customer_service'])
def search_customers():
    """Search customers with filters"""
    try:
        search_params = {
            'postal_code': request.args.get('postal_code'),
            'housing_type': request.args.get('housing_type'),
            'contact': request.args.get('contact'),
            'street': request.args.get('street'),
            'limit': request.args.get('limit', 50),
            'offset': request.args.get('offset', 0)
        }
        
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        result, status = CustomerService.search_customers(search_params)
        return jsonify(result), status
        
    except Exception as e:
        logger.error(f"Search customers endpoint error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/customers/validate', methods=['POST'])
@role_required(['admin', 'hq', 'customer_service'])
def validate_customer_data():
    """Validate customer data without saving"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        validation_errors = CustomerValidationService.validate_customer_data(data)
        
        if validation_errors:
            return jsonify({
                "valid": False,
                "errors": validation_errors
            }), 400
        else:
            return jsonify({
                "valid": True,
                "message": "Customer data is valid"
            }), 200
        
    except Exception as e:
        logger.error(f"Validate customer data endpoint error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=Config.SERVICE_PORT)