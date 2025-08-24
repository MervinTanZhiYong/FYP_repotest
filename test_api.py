# API Testing Script for Levels Living Microservices
# Run this script to test UserMS and CustomerMS endpoints

import requests
import json
from datetime import datetime

# Configuration
BASE_URL_USER = "http://localhost:5001"
BASE_URL_CUSTOMER = "http://localhost:5002"

# Global variables to store tokens
access_token = None
refresh_token = None
session_id = None

def print_separator(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_response(response, description):
    print(f"\n{description}")
    print(f"Status Code: {response.status_code}")
    try:
        response_json = response.json()
        print(f"Response: {json.dumps(response_json, indent=2)}")
        return response_json
    except:
        print(f"Response Text: {response.text}")
        return None

def test_health_checks():
    print_separator("HEALTH CHECKS")
    
    # Test UserMS health
    response = requests.get(f"{BASE_URL_USER}/health")
    print_response(response, "UserMS Health Check")
    
    # Test CustomerMS health
    response = requests.get(f"{BASE_URL_CUSTOMER}/health")
    print_response(response, "CustomerMS Health Check")

def test_user_registration():
    print_separator("USER REGISTRATION TESTS")
    
    # Test valid registration
    user_data = {
        "email": "admin@levels.sg",
        "password": "password123",
        "role": "admin"
    }
    response = requests.post(f"{BASE_URL_USER}/auth/register", json=user_data)
    print_response(response, "Register Admin User")
    
    # Test another user for customer service
    cs_user_data = {
        "email": "cs@levels.sg", 
        "password": "password123",
        "role": "customer_service"
    }
    response = requests.post(f"{BASE_URL_USER}/auth/register", json=cs_user_data)
    print_response(response, "Register Customer Service User")
    
    # Test invalid email format
    invalid_user = {
        "email": "invalid-email",
        "password": "password123",
        "role": "admin"
    }
    response = requests.post(f"{BASE_URL_USER}/auth/register", json=invalid_user)
    print_response(response, "Register with Invalid Email (should fail)")
    
    # Test duplicate registration
    response = requests.post(f"{BASE_URL_USER}/auth/register", json=user_data)
    print_response(response, "Duplicate Registration (should fail)")

def test_user_login():
    global access_token, refresh_token, session_id
    print_separator("USER LOGIN TESTS")
    
    # Test valid login
    login_data = {
        "email": "admin@levels.sg",
        "password": "password123"
    }
    response = requests.post(f"{BASE_URL_USER}/auth/login", json=login_data)
    result = print_response(response, "Valid Login")
    
    if response.status_code == 200 and result:
        access_token = result.get('access_token')
        refresh_token = result.get('refresh_token')
        session_id = result.get('session_id')
        print(f"Stored access token: {access_token[:50]}...")
    
    # Test invalid credentials
    invalid_login = {
        "email": "admin@levels.sg",
        "password": "wrongpassword"
    }
    response = requests.post(f"{BASE_URL_USER}/auth/login", json=invalid_login)
    print_response(response, "Invalid Login (should fail)")
    
    # Test missing credentials
    incomplete_login = {
        "email": "admin@levels.sg"
    }
    response = requests.post(f"{BASE_URL_USER}/auth/login", json=incomplete_login)
    print_response(response, "Missing Password (should fail)")

def test_protected_user_endpoints():
    print_separator("PROTECTED USER ENDPOINTS")
    
    if not access_token:
        print("No access token available. Skipping protected endpoint tests.")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test get profile
    response = requests.get(f"{BASE_URL_USER}/auth/profile", headers=headers)
    print_response(response, "Get User Profile")
    
    # Test token validation
    response = requests.post(f"{BASE_URL_USER}/auth/validate", headers=headers)
    print_response(response, "Validate Token")
    
    # Test list users (admin only)
    response = requests.get(f"{BASE_URL_USER}/auth/users", headers=headers)
    print_response(response, "List Users (Admin Only)")
    
    # Test logout
    logout_data = {"session_id": session_id} if session_id else {}
    response = requests.post(f"{BASE_URL_USER}/auth/logout", json=logout_data, headers=headers)
    print_response(response, "User Logout")

def test_customer_creation():
    print_separator("CUSTOMER CREATION TESTS")
    
    if not access_token:
        print("No access token available. Skipping customer tests.")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test valid customer creation
    customer_data = {
        "customer_contact": "+6591234567",
        "customer_street": "123 Orchard Road",
        "customer_unit": "#12-34",
        "customer_postal_code": "238123",
        "housing_type": "Condo",
        "delivery_preferences": {
            "preferred_time": "morning",
            "special_instructions": "Call before delivery"
        },
        "communication_preferences": {
            "sms": True,
            "email": False
        }
    }
    response = requests.post(f"{BASE_URL_CUSTOMER}/customers", json=customer_data, headers=headers)
    result = print_response(response, "Create Valid Customer")
    
    # Store customer ID for later tests
    customer_id = None
    if response.status_code == 201 and result:
        customer_id = result.get('customer', {}).get('customer_id')
        print(f"Created customer ID: {customer_id}")
    
    # Test another customer
    customer_data2 = {
        "customer_contact": "+6598765432",
        "customer_street": "456 Marina Bay",
        "customer_unit": "#05-67",
        "customer_postal_code": "179103",
        "housing_type": "HDB"
    }
    response = requests.post(f"{BASE_URL_CUSTOMER}/customers", json=customer_data2, headers=headers)
    print_response(response, "Create Second Customer")
    
    # Test invalid contact format
    invalid_customer = {
        "customer_contact": "1234567",  # Invalid format
        "customer_postal_code": "238123"
    }
    response = requests.post(f"{BASE_URL_CUSTOMER}/customers", json=invalid_customer, headers=headers)
    print_response(response, "Invalid Contact Format (should fail)")
    
    # Test duplicate customer
    response = requests.post(f"{BASE_URL_CUSTOMER}/customers", json=customer_data, headers=headers)
    print_response(response, "Duplicate Customer (should fail)")
    
    return customer_id

def test_customer_retrieval(customer_id):
    print_separator("CUSTOMER RETRIEVAL TESTS")
    
    if not access_token:
        print("No access token available. Skipping customer retrieval tests.")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    if customer_id:
        # Test get customer by ID
        response = requests.get(f"{BASE_URL_CUSTOMER}/customers/{customer_id}", headers=headers)
        print_response(response, "Get Customer by ID")
        
        # Test get customer by contact
        response = requests.get(f"{BASE_URL_CUSTOMER}/customers/contact/+6591234567", headers=headers)
        print_response(response, "Get Customer by Contact")
    
    # Test search customers
    response = requests.get(f"{BASE_URL_CUSTOMER}/customers", headers=headers)
    print_response(response, "Search All Customers")
    
    # Test search with filters
    params = {"housing_type": "Condo", "limit": 10}
    response = requests.get(f"{BASE_URL_CUSTOMER}/customers", params=params, headers=headers)
    print_response(response, "Search Customers with Filters")
    
    # Test non-existent customer
    response = requests.get(f"{BASE_URL_CUSTOMER}/customers/nonexistent-id", headers=headers)
    print_response(response, "Get Non-existent Customer (should fail)")

def test_customer_validation():
    print_separator("CUSTOMER VALIDATION TESTS")
    
    if not access_token:
        print("No access token available. Skipping validation tests.")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test valid customer data
    valid_data = {
        "customer_contact": "+6587654321",
        "customer_postal_code": "560123",
        "housing_type": "HDB"
    }
    response = requests.post(f"{BASE_URL_CUSTOMER}/customers/validate", json=valid_data, headers=headers)
    print_response(response, "Validate Valid Customer Data")
    
    # Test invalid customer data
    invalid_data = {
        "customer_contact": "invalid",
        "customer_postal_code": "123",  # Too short
        "housing_type": "InvalidType"
    }
    response = requests.post(f"{BASE_URL_CUSTOMER}/customers/validate", json=invalid_data, headers=headers)
    print_response(response, "Validate Invalid Customer Data (should fail)")

def test_unauthorized_access():
    print_separator("UNAUTHORIZED ACCESS TESTS")
    
    # Test accessing protected endpoints without token
    response = requests.get(f"{BASE_URL_USER}/auth/profile")
    print_response(response, "Access Profile Without Token (should fail)")
    
    response = requests.get(f"{BASE_URL_CUSTOMER}/customers")
    print_response(response, "Access Customers Without Token (should fail)")
    
    # Test with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    response = requests.get(f"{BASE_URL_USER}/auth/profile", headers=invalid_headers)
    print_response(response, "Access Profile With Invalid Token (should fail)")

def test_edge_cases():
    print_separator("EDGE CASE TESTS")
    
    # Test empty JSON
    response = requests.post(f"{BASE_URL_USER}/auth/login", json={})
    print_response(response, "Login with Empty JSON (should fail)")
    
    # Test malformed JSON
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{BASE_URL_USER}/auth/login", data="invalid json", headers=headers)
    print_response(response, "Login with Malformed JSON (should fail)")
    
    # Test very long postal code
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        long_postal_data = {
            "customer_contact": "+6599999999",
            "customer_postal_code": "1234567890123456"  # Too long
        }
        response = requests.post(f"{BASE_URL_CUSTOMER}/customers", json=long_postal_data, headers=headers)
        print_response(response, "Customer with Long Postal Code (should fail)")

def run_all_tests():
    print_separator("STARTING API TESTS")
    print(f"Timestamp: {datetime.now()}")
    print(f"UserMS URL: {BASE_URL_USER}")
    print(f"CustomerMS URL: {BASE_URL_CUSTOMER}")
    
    try:
        # Run all test suites
        test_health_checks()
        test_user_registration()
        test_user_login()
        test_protected_user_endpoints()
        
        # Re-login for customer tests (since we logged out)
        print_separator("RE-LOGIN FOR CUSTOMER TESTS")
        login_data = {"email": "admin@levels.sg", "password": "password123"}
        response = requests.post(f"{BASE_URL_USER}/auth/login", json=login_data)
        if response.status_code == 200:
            global access_token
            access_token = response.json().get('access_token')
            print("Successfully re-logged in for customer tests")
        
        customer_id = test_customer_creation()
        test_customer_retrieval(customer_id)
        test_customer_validation()
        test_unauthorized_access()
        test_edge_cases()
        
        print_separator("ALL TESTS COMPLETED")
        print("Check the results above for any failures or issues.")
        
    except requests.exceptions.ConnectionError as e:
        print(f"\nConnection Error: {e}")
        print("Make sure your services are running:")
        print("- docker-compose ps")
        print("- docker-compose logs user-auth-service")
        print("- docker-compose logs customer-service")
    except Exception as e:
        print(f"\nUnexpected Error: {e}")

if __name__ == "__main__":
    run_all_tests()