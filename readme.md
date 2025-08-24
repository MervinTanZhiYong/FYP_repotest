# Levels Living - Last Mile Delivery System

## Microservices Architecture

This project implements a microservices-based last mile delivery system for Levels Living, consisting of:

1. **User Authentication Service** - Handles user registration, login, JWT token management
2. **Customer Service** - Manages customer information, addresses, and preferences
3. **MySQL Database** - Primary data storage
4. **Redis** - Session management and caching
5. **API Gateway** - Request routing and load balancing

- Docker & Docker Compose
- MySQL
- Redis 
- Python 3.13 (for development)


1. **Clone and Setup**
   ```bash
   git clone <your-repo>
   cd levels-living-delivery-system
   ```

2. **Create Project Structure**
   ```
   levels-living-delivery-system/
   ├── docker-compose.yml
   ├── database.sql
   ├── user_auth_service/
   │   ├── app.py
   │   ├── requirements.txt
   │   └── Dockerfile
   ├── customer_service/
   │   ├── app.py
   │   ├── requirements.txt
   │   └── Dockerfile
   └── test_api.py
   ```

3. **Start Services**
   ```bash
   # Start all services
   docker-compose up -d
   
   # View logs
   docker-compose logs -f
   
   # Start with development tools (phpMyAdmin, Redis Commander)
   docker-compose --profile dev up -d
   ```

4. **Verify Services**
   ```bash
   # Check service health
   curl http://localhost:5001/health  # Auth Service
   curl http://localhost:5002/health  # Customer Service
   ```

### Option 2: Local Development

1. **Setup MySQL Database**
   ```bash
   # Create database
   mysql -u root -p
   CREATE DATABASE levels_living_db;
   
   # Import schema
   mysql -u root -p levels_living_db < mysql_schema.sql
   ```

2. **Setup Redis**
   ```bash
   # Install and start Redis
   redis-server
   ```

3. **Setup User Auth Service**
   ```bash
   cd user_auth_service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Set environment variables
   export DB_HOST=localhost
   export DB_NAME=levels_living_db
   export DB_USER=root
   export DB_PASSWORD=your_password
   export REDIS_HOST=localhost
   export JWT_SECRET_KEY=your-jwt-secret
   
   # Run service
   python app.py
   ```

4. **Setup Customer Service**
   ```bash
   cd customer_service
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Set same environment variables as above
   python app.py
   ```

## 🧪 Testing

### Run API Tests
```bash
# Install test dependencies
pip install requests

# Run comprehensive API tests
python test_api.py
```

### Manual Testing with curl

1. **Register User**
   ```bash
   curl -X POST http://localhost:5001/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@levels.sg",
       "password": "password123",
       "role": "admin"
     }'
   ```

2. **Login**
   ```bash
   curl -X POST http://localhost:5001/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@levels.sg",
       "password": "password123"
     }'
   ```

3. **Create Customer** (use token from login)
   ```bash
   curl -X POST http://localhost:5002/customers \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "customer_contact": "+6591234567",
       "customer_street": "123 Test Street",
       "customer_postal_code": "560123",
       "housing_type": "HDB"
     }'
   ```

## 📊 Admin Interfaces

When running with `--profile dev`:

- **phpMyAdmin**: http://localhost:8080
  - Server: mysql
  - Username: levels_user
  - Password: levels_password

- **Redis Commander**: http://localhost:8081

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | MySQL host | localhost |
| `DB_NAME` | Database name | levels_living_db |
| `DB_USER` | Database user | root |
| `DB_PASSWORD` | Database password | (empty) |
| `REDIS_HOST` | Redis host | localhost |
| `JWT_SECRET_KEY` | JWT signing key | (change in production) |
| `SECRET_KEY` | Flask secret key | (change in production) |

### Service Ports

- User Auth Service: 5001
- Customer Service: 5002
- MySQL: 3306
- Redis: 6379
- phpMyAdmin: 8080 (dev only)
- Redis Commander: 8081 (dev only)

## 🏗️ Architecture Overview

### User Authentication Service (Port 5001)
- **POST** `/auth/register` - Register new user
- **POST** `/auth/login` - User login
- **POST** `/auth/refresh` - Refresh access token
- **GET** `/auth/profile` - Get user profile
- **PUT** `/auth/profile` - Update user profile
- **POST** `/auth/change-password` - Change password
- **POST** `/auth/logout` - User logout
- **GET** `/auth/users` - List users (admin only)
- **POST** `/auth/validate` - Validate JWT token

### Customer Service (Port 5002)
- **POST** `/customers` - Create customer
- **GET** `/customers/{id}` - Get customer by ID
- **GET** `/customers/contact/{contact}` - Get customer by contact
- **GET** `/customers` - Search customers
- **PUT** `/customers/{id}` - Update customer
- **DELETE** `/customers/{id}` - Deactivate customer
- **GET** `/customers/area/{postal_prefix}` - Get customers by area
- **POST** `/customers/validate` - Validate customer data
- **POST** `/customers/bulk` - Bulk create customers

### Security Features
- JWT-based authentication with access/refresh tokens
- Role-based access control (admin, hq, warehouse, driver, customer_service)
- Account lockout after failed login attempts
- Session management with Redis
- Password hashing with bcrypt
- Input validation and sanitization

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if MySQL is running
   docker-compose ps mysql
   
   # Check MySQL logs
   docker-compose logs mysql
   ```

2. **Service Health Check Failed**
   ```bash
   # Check service logs
   docker-compose logs user-auth-service
   docker-compose logs customer-service
   ```

3. **Port Already in Use**
   ```bash
   # Find process using port
   lsof -i :5001
   
   # Kill process
   kill -9 <PID>
   ```

4. **JWT Token Issues**
   - Ensure JWT_SECRET_KEY is consistent across services
   - Check token expiration times
   - Verify Redis is running for token blacklisting

### Reset Everything
```bash
# Stop and remove all containers, volumes, and networks
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up -d
```

## Upcoming Steps -

1. **Add Order Management Service**
2. **Implement Inventory Service** 
3. **Create Delivery Service with route optimization**
4. **Add Notification Service for SMS/Email**
5. **Implement Analytics Service**
6. **Create next.js Frontend**
7. **Add API Gateway**
8. **Implement monitoring and logging (PDF Generator)**


That's all for now updated @ 21st August 2025 11.00pm