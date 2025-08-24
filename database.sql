-- ============================
-- LEVELS LIVING LAST MILE DELIVERY SYSTEM
-- MySQL Database Schema
-- Microservices Architecture
-- ============================

-- Create main database
CREATE DATABASE IF NOT EXISTS levels_living_db;
USE levels_living_db;

-- ============================
-- CORE TABLES
-- ============================

-- Users Table (User Authentication Service)
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    role ENUM('admin', 'warehouse', 'driver', 'hq', 'customer_service') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_users_email (email),
    INDEX idx_users_role (role),
    INDEX idx_users_active (is_active)
);

-- User Sessions (User Authentication Service)
CREATE TABLE user_sessions (
    session_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36) NOT NULL,
    refresh_token_hash VARCHAR(200) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45),
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_sessions_user_id (user_id),
    INDEX idx_sessions_expires (expires_at)
);

-- Customers Table (Customer Service)
CREATE TABLE customers (
    customer_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    customer_contact VARCHAR(20) UNIQUE NOT NULL,
    customer_street VARCHAR(200),
    customer_unit VARCHAR(20),
    customer_postal_code VARCHAR(6) NOT NULL,
    housing_type ENUM('HDB', 'Condo', 'Landed', 'Commercial'),
    delivery_preferences JSON,
    communication_preferences JSON DEFAULT ('{"sms": true, "email": false}'),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_customers_contact (customer_contact),
    INDEX idx_customers_postal (customer_postal_code),
    INDEX idx_customers_location (latitude, longitude),
    CONSTRAINT chk_postal_code CHECK (customer_postal_code REGEXP '^[0-9]{6}$'),
    CONSTRAINT chk_contact CHECK (customer_contact REGEXP '^(\\+65)?[689][0-9]{7}$')
);

-- Orders Table (Order Management Service)
CREATE TABLE orders (
    order_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    order_no VARCHAR(50) UNIQUE NOT NULL,
    shopify_order_id VARCHAR(50),
    platform_order_id VARCHAR(50),
    customer_id VARCHAR(36) NOT NULL,
    status ENUM(
        'received', 'validated', 'processing', 'in_assembly', 
        'ready_for_delivery', 'out_for_delivery', 'delivered', 
        'failed', 'cancelled', 'returned'
    ) DEFAULT 'received',
    order_date DATE NOT NULL,
    order_value DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'SGD',
    tag VARCHAR(100),
    note TEXT,
    custom_fields JSON,
    special_delivery BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 1,
    source_system VARCHAR(50) DEFAULT 'shopify',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_status (status),
    INDEX idx_orders_date (order_date),
    INDEX idx_orders_no (order_no),
    CONSTRAINT chk_order_value CHECK (order_value >= 0)
);

-- Order Items Table (Inventory Service)
CREATE TABLE order_items (
    item_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    order_id VARCHAR(36) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    variant VARCHAR(100),
    quantity INT NOT NULL DEFAULT 1,
    assembled BOOLEAN DEFAULT FALSE,
    image_url VARCHAR(500),
    weight DECIMAL(8,2),
    volume DECIMAL(8,2),
    special_handling BOOLEAN DEFAULT FALSE,
    assembly_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    INDEX idx_order_items_order (order_id),
    INDEX idx_order_items_sku (sku),
    INDEX idx_order_items_assembled (assembled),
    CONSTRAINT chk_quantity CHECK (quantity > 0)
);

-- Inventory Table (Inventory Service)
CREATE TABLE inventory (
    sku VARCHAR(100) PRIMARY KEY,
    item_name VARCHAR(200) NOT NULL,
    current_stock INT NOT NULL DEFAULT 0,
    reserved_stock INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 5,
    max_stock_level INT DEFAULT 1000,
    unit_cost DECIMAL(10,2),
    selling_price DECIMAL(10,2),
    supplier VARCHAR(200),
    weight_per_unit DECIMAL(8,2),
    volume_per_unit DECIMAL(8,2),
    dimensions JSON,
    special_handling_required BOOLEAN DEFAULT FALSE,
    storage_location VARCHAR(50),
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_inventory_reorder (current_stock, reorder_level),
    INDEX idx_inventory_category (category),
    CONSTRAINT chk_current_stock CHECK (current_stock >= 0),
    CONSTRAINT chk_reserved_stock CHECK (reserved_stock >= 0)
);

-- Drivers Table (Delivery Service)
CREATE TABLE drivers (
    driver_id VARCHAR(20) PRIMARY KEY,
    driver_name VARCHAR(100) NOT NULL,
    driver_contact VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(200),
    team VARCHAR(50),
    license_number VARCHAR(20) UNIQUE,
    license_expiry DATE,
    vehicle_type ENUM('van', 'truck', 'motorcycle', 'car'),
    vehicle_plate VARCHAR(20) UNIQUE,
    vehicle_capacity_kg DECIMAL(8,2),
    vehicle_capacity_cbm DECIMAL(8,2),
    max_delivery_items INT,
    status ENUM('available', 'on_delivery', 'off_duty', 'maintenance', 'on_leave') DEFAULT 'available',
    base_hourly_rate DECIMAL(8,2),
    overtime_rate DECIMAL(4,2) DEFAULT 1.5,
    weekend_rate DECIMAL(4,2) DEFAULT 2.0,
    performance_rating DECIMAL(3,2) DEFAULT 5.0,
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_drivers_status (status),
    INDEX idx_drivers_team (team),
    CONSTRAINT chk_driver_contact CHECK (driver_contact REGEXP '^(\\+65)?[689][0-9]{7}$')
);

-- Routes Table (Delivery Service)
CREATE TABLE routes (
    route_id VARCHAR(50) PRIMARY KEY,
    driver_id VARCHAR(20),
    team VARCHAR(50),
    route_date DATE NOT NULL,
    route_type ENUM('regular', 'adhoc_single_delivery', 'split_load', 'return_trip') DEFAULT 'regular',
    start_location JSON NOT NULL,
    end_location JSON,
    waypoints JSON,
    route_data JSON,
    total_distance DECIMAL(8,2),
    estimated_time INT,
    actual_time INT,
    fuel_cost DECIMAL(8,2),
    toll_cost DECIMAL(8,2),
    additional_cost DECIMAL(10,2) DEFAULT 0.00,
    overtime_hours DECIMAL(4,2) DEFAULT 0.00,
    overtime_applicable BOOLEAN DEFAULT FALSE,
    weekend_surcharge BOOLEAN DEFAULT FALSE,
    status ENUM('planned', 'assigned', 'in_progress', 'completed', 'cancelled') DEFAULT 'planned',
    optimization_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id) ON DELETE SET NULL,
    INDEX idx_routes_driver (driver_id),
    INDEX idx_routes_date (route_date),
    INDEX idx_routes_status (status)
);

-- Deliveries Table (Delivery Service)
CREATE TABLE deliveries (
    delivery_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    order_id VARCHAR(36) NOT NULL,
    route_id VARCHAR(50),
    delivery_date DATE NOT NULL,
    delivery_time_start TIME,
    delivery_time_end TIME,
    delivery_order INT,
    team VARCHAR(50),
    driver_id VARCHAR(20),
    customer_id VARCHAR(36) NOT NULL,
    delivery_address JSON NOT NULL,
    delivered BOOLEAN DEFAULT FALSE,
    signature_data TEXT,
    delivery_photos JSON,
    delivery_notes TEXT,
    customer_feedback JSON,
    status ENUM(
        'scheduled', 'scheduled_adhoc', 'assigned', 'dispatched', 'in_transit', 
        'arrived', 'delivered', 'failed', 'rescheduled', 'returned', 'cancelled'
    ) DEFAULT 'scheduled',
    failure_reason TEXT,
    attempted_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    delivery_duration INT,
    special_instructions TEXT,
    customer_availability_window VARCHAR(50),
    requires_appointment BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE SET NULL,
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    INDEX idx_deliveries_order (order_id),
    INDEX idx_deliveries_driver (driver_id),
    INDEX idx_deliveries_date (delivery_date),
    INDEX idx_deliveries_status (status)
);

-- Communications Table (Notification Service)
CREATE TABLE communications (
    communication_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    order_id VARCHAR(36),
    customer_id VARCHAR(36),
    communication_type ENUM('sms', 'email', 'push_notification', 'whatsapp', 'voice_call') NOT NULL,
    message_type ENUM(
        'order_confirmation', 'delivery_scheduled', 'delivery_update', 
        'delivery_completed', 'adhoc_delivery_confirmation', 'delivery_failed', 
        'rescheduled', 'reminder', 'feedback_request', 'promotional'
    ) NOT NULL,
    recipient_contact VARCHAR(50) NOT NULL,
    recipient_name VARCHAR(100),
    subject TEXT,
    message_content TEXT NOT NULL,
    scheduled_at TIMESTAMP NULL,
    sent_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,
    status ENUM('pending', 'scheduled', 'sent', 'delivered', 'read', 'failed', 'cancelled', 'bounced') DEFAULT 'pending',
    failure_reason TEXT,
    external_message_id VARCHAR(100),
    external_status VARCHAR(50),
    delivery_confirmation JSON,
    priority ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
    cost DECIMAL(6,4),
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    INDEX idx_communications_order (order_id),
    INDEX idx_communications_customer (customer_id),
    INDEX idx_communications_status (status),
    INDEX idx_communications_type (communication_type),
    INDEX idx_communications_sent (sent_at),
    INDEX idx_communications_scheduled (scheduled_at)
);

-- Assembly Queue Table (Inventory Service)
CREATE TABLE assembly_queue (
    queue_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    order_id VARCHAR(36) NOT NULL,
    item_id VARCHAR(36) NOT NULL,
    priority INT DEFAULT 1,
    assigned_to VARCHAR(36),
    status ENUM('pending', 'in_progress', 'completed', 'defective', 'on_hold') DEFAULT 'pending',
    estimated_time INT,
    actual_time INT,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES order_items(item_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_assembly_queue_order (order_id),
    INDEX idx_assembly_queue_status (status),
    INDEX idx_assembly_queue_priority (priority)
);

-- Defects Tracking Table (Inventory Service)
CREATE TABLE defects (
    defect_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    item_id VARCHAR(36) NOT NULL,
    order_id VARCHAR(36) NOT NULL,
    defect_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    reported_by VARCHAR(36),
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    status ENUM('reported', 'investigating', 'resolved', 'replaced') DEFAULT 'reported',
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    
    FOREIGN KEY (item_id) REFERENCES order_items(item_id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_defects_item (item_id),
    INDEX idx_defects_order (order_id),
    INDEX idx_defects_status (status)
);

-- System Events Table (Analytics Service)
CREATE TABLE system_events (
    event_id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    event_type VARCHAR(50) NOT NULL,
    service_name VARCHAR(50) NOT NULL,
    entity_type VARCHAR(30) NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    event_data JSON,
    user_id VARCHAR(36),
    session_id VARCHAR(36),
    ip_address VARCHAR(45),
    user_agent TEXT,
    correlation_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_system_events_service (service_name),
    INDEX idx_system_events_type (event_type),
    INDEX idx_system_events_entity (entity_type, entity_id),
    INDEX idx_system_events_user (user_id),
    INDEX idx_system_events_created (created_at)
);

-- ============================
-- SAMPLE DATA
-- ============================

-- Insert sample users
INSERT INTO users (email, password_hash, role) VALUES
('admin@levels.sg', '$2b$12$example_hash_admin', 'admin'),
('warehouse@levels.sg', '$2b$12$example_hash_warehouse', 'warehouse'),
('driver1@levels.sg', '$2b$12$example_hash_driver1', 'driver'),
('hq@levels.sg', '$2b$12$example_hash_hq', 'hq'),
('cs@levels.sg', '$2b$12$example_hash_cs', 'customer_service');

-- Insert sample customers
INSERT INTO customers (customer_contact, customer_street, customer_unit, customer_postal_code, housing_type, latitude, longitude) VALUES
('+6591234567', '123 Ang Mo Kio Ave 1', '#12-34', '560123', 'HDB', 1.3701, 103.8454),
('+6598765432', '456 Orchard Road', '#05-67', '238123', 'Condo', 1.3048, 103.8198),
('+6587654321', '789 Bukit Timah Road', 'House 1', '259012', 'Landed', 1.3387, 103.7890);

-- Insert sample inventory
INSERT INTO inventory (sku, item_name, current_stock, reserved_stock, reorder_level, weight_per_unit, volume_per_unit, special_handling_required) VALUES
('SKU001', 'Office Chair Model A', 50, 5, 10, 12.5, 0.3, FALSE),
('SKU002', 'Standing Desk 120cm', 25, 2, 5, 45.0, 2.1, TRUE),
('SKU003', 'Storage Cabinet White', 30, 3, 8, 25.0, 1.5, FALSE);

-- Insert sample drivers
INSERT INTO drivers (driver_id, driver_name, driver_contact, team, license_number, vehicle_type, vehicle_plate, vehicle_capacity_kg, vehicle_capacity_cbm, max_delivery_items, base_hourly_rate) VALUES
('DRV001', 'John Tan', '+6591111111', 'Team A', 'DL123456', 'van', 'SJH1234A', 1000.00, 8.0, 20, 25.00),
('DRV002', 'Mary Lim', '+6592222222', 'Team B', 'DL789012', 'truck', 'SJH5678B', 2000.00, 15.0, 50, 28.00),
('DRV003', 'David Wong', '+6593333333', 'Adhoc Team', 'DL345678', 'van', 'SJH9012C', 1000.00, 8.0, 20, 30.00);

-- ============================
-- VIEWS FOR COMMON QUERIES
-- ============================

-- Order summary view
CREATE VIEW order_summary AS
SELECT 
    o.order_id,
    o.order_no,
    o.status,
    o.order_date,
    o.order_value,
    c.customer_contact,
    c.customer_postal_code,
    c.housing_type,
    COUNT(oi.item_id) as total_items,
    COUNT(CASE WHEN oi.assembled = TRUE THEN 1 END) as assembled_items
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, c.customer_id;

-- Delivery schedule view
CREATE VIEW delivery_schedule AS
SELECT 
    d.delivery_id,
    d.delivery_date,
    d.delivery_time_start,
    d.delivery_time_end,
    d.delivery_order,
    d.status,
    o.order_no,
    c.customer_contact,
    c.customer_street,
    c.customer_postal_code,
    dr.driver_name,
    d.team
FROM deliveries d
JOIN orders o ON d.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN drivers dr ON d.driver_id = dr.driver_id
ORDER BY d.delivery_date, d.delivery_order;

-- Inventory alerts view
CREATE VIEW inventory_alerts AS
SELECT 
    sku,
    item_name,
    current_stock,
    reserved_stock,
    reorder_level,
    (current_stock - reserved_stock) as available_stock,
    CASE 
        WHEN current_stock <= reorder_level THEN 'REORDER_NEEDED'
        WHEN (current_stock - reserved_stock) <= 0 THEN 'OUT_OF_STOCK'
        WHEN (current_stock - reserved_stock) <= reorder_level THEN 'LOW_STOCK'
        ELSE 'OK'
    END as stock_status
FROM inventory
WHERE current_stock <= reorder_level OR (current_stock - reserved_stock) <= reorder_level;