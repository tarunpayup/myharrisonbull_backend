# API Documentation

## Overview

The Harrison Bull API is a comprehensive REST API built with Flask and SQLAlchemy for the e-commerce platform. All endpoints return JSON responses with appropriate HTTP status codes.

## Base URL

**Development**: `http://localhost:5000`
**Production**: `https://harrison-bull-api.onrender.com` (or your Render URL)

## Authentication

Most endpoints require JWT (JSON Web Token) authentication. Include the token in the request header:

```
Authorization: Bearer <your_jwt_token>
```

## HTTP Status Codes

- `200` - OK: Request successful
- `201` - Created: Resource created successfully
- `400` - Bad Request: Invalid input or missing required fields
- `401` - Unauthorized: Invalid or missing authentication
- `403` - Forbidden: Access denied (e.g., non-admin access to admin endpoints)
- `404` - Not Found: Resource not found
- `500` - Internal Server Error: Server error

## Response Format

All responses follow this format:

**Success Response:**
```json
{
  "data": { ... },
  "message": "Success message"
}
```

**Error Response:**
```json
{
  "error": "Error message"
}
```

---

# Endpoints

## Authentication Endpoints

### Register User
Create a new user account.

**Endpoint**: `POST /api/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response** (201):
```json
{
  "message": "User created successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### Login User
Authenticate user and get JWT token.

**Endpoint**: `POST /api/auth/login`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response** (200):
```json
{
  "message": "Login successful",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_admin": false
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### Get Current User
Retrieve authenticated user's profile.

**Endpoint**: `GET /api/auth/me`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "avatar_url": "https://...",
    "newsletter_subscribed": true,
    "promotions_enabled": true,
    "is_admin": false,
    "created_at": "2024-01-01T12:00:00"
  }
}
```

---

### Logout
Logout user (stateless operation).

**Endpoint**: `POST /api/auth/logout`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "message": "Logout successful"
}
```

---

### Forgot Password
Request a password reset link.

**Endpoint**: `POST /api/auth/forgot-password`

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200):
```json
{
  "message": "If email exists, password reset link will be sent"
}
```

---

### Reset Password
Reset password using token.

**Endpoint**: `POST /api/auth/reset-password`

**Request Body**:
```json
{
  "token": "reset-token",
  "password": "newpassword"
}
```

**Response** (200):
```json
{
  "message": "Password reset successful"
}
```

---

## Products Endpoints

### List Products
Get paginated list of products with filtering and sorting.

**Endpoint**: `GET /api/products`

**Query Parameters**:
- `page` (int, default: 1) - Page number
- `limit` (int, default: 10) - Items per page
- `category_id` (string) - Filter by category
- `search` (string) - Search by title or description
- `sort_by` (string) - Sort option: `created_at`, `price_asc`, `price_desc`, `rating`

**Response** (200):
```json
{
  "products": [
    {
      "id": "uuid",
      "title": "Premium Leather Oxford",
      "slug": "premium-leather-oxford",
      "price": 299.99,
      "original_price": 399.99,
      "discount_percent": 25.0,
      "color": "Black",
      "rating": 4.5,
      "reviews_count": 42,
      "is_best_seller": true,
      "is_featured": false,
      "is_new": false,
      "in_stock": true
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 150,
    "pages": 15
  }
}
```

---

### Get Product Details
Get detailed information about a specific product.

**Endpoint**: `GET /api/products/<product_id>`

**Response** (200):
```json
{
  "id": "uuid",
  "title": "Premium Leather Oxford",
  "slug": "premium-leather-oxford",
  "sku": "PLO-001",
  "price": 299.99,
  "original_price": 399.99,
  "discount_percent": 25.0,
  "short_description": "Classic oxford shoes",
  "description": "Handcrafted premium leather oxford...",
  "color": "Black",
  "color_hex": "#000000",
  "rating": 4.5,
  "reviews_count": 42,
  "is_best_seller": true,
  "is_featured": false,
  "is_new": false,
  "in_stock": true,
  "specifications": {
    "welt_type": "Goodyear Welted",
    "leather_type": "Full Grain Calf",
    "sole_type": "Leather",
    "last_name": "Classic",
    "lining_material": "Leather",
    "crafting_time_hours": 8,
    "is_resolable": true,
    "origin_location": "England"
  },
  "images": [
    {
      "id": "uuid",
      "url": "https://...",
      "alt_text": "Front view",
      "is_primary": true
    }
  ],
  "sizes": {
    "7": 5,
    "8": 3,
    "9": 0
  }
}
```

---

### Search Products
Quick product search.

**Endpoint**: `GET /api/products/search`

**Query Parameters**:
- `q` (string, required) - Search query (minimum 2 characters)

**Response** (200):
```json
{
  "results": [
    {
      "id": "uuid",
      "title": "Oxford Shoes",
      "slug": "oxford-shoes",
      "price": 299.99,
      "rating": 4.5,
      "color": "Black"
    }
  ]
}
```

---

### Get Product by Slug
Get product using URL-friendly slug.

**Endpoint**: `GET /api/products/by-slug/<slug>`

**Response**: Same as "Get Product Details"

---

### Get Categories
Get all product categories.

**Endpoint**: `GET /api/products/categories`

**Response** (200):
```json
{
  "categories": [
    {
      "id": "uuid",
      "name": "Oxfords",
      "slug": "oxfords",
      "description": "Classic oxford shoes",
      "image_url": "https://..."
    }
  ]
}
```

---

## Orders Endpoints

### Create Order
Create a new order.

**Endpoint**: `POST /api/orders`

**Request Body**:
```json
{
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "customer_phone": "+1234567890",
  "items": [
    {
      "product_id": "uuid",
      "product_title": "Oxford Shoes",
      "size": "9",
      "quantity": 2,
      "price": 299.99
    }
  ],
  "subtotal": 599.98,
  "tax": 47.99,
  "shipping_cost": 15.00,
  "discount_amount": 50.00,
  "coupon_id": "uuid or null",
  "shipping_address": {
    "street": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "postal_code": "62701",
    "country": "USA"
  },
  "payment_method": "credit_card"
}
```

**Response** (201):
```json
{
  "message": "Order created successfully",
  "order": {
    "id": "uuid",
    "order_number": "ORD-20240101-A1B2C3D4",
    "total": 612.97,
    "status": "Pending",
    "payment_status": "Pending"
  }
}
```

---

### Get User Orders
Get all orders for authenticated user.

**Endpoint**: `GET /api/orders`

**Headers Required**: Authorization

**Query Parameters**:
- `page` (int, default: 1)
- `limit` (int, default: 10)

**Response** (200):
```json
{
  "orders": [
    {
      "id": "uuid",
      "order_number": "ORD-20240101-A1B2C3D4",
      "total": 612.97,
      "status": "Completed",
      "payment_status": "Completed",
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 5,
    "pages": 1
  }
}
```

---

### Get Order Details
Get detailed information about a specific order.

**Endpoint**: `GET /api/orders/<order_id>`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "id": "uuid",
  "order_number": "ORD-20240101-A1B2C3D4",
  "customer_name": "John Doe",
  "customer_email": "user@example.com",
  "customer_phone": "+1234567890",
  "subtotal": 599.98,
  "tax": 47.99,
  "shipping_cost": 15.00,
  "discount_amount": 50.00,
  "total": 612.97,
  "status": "Completed",
  "payment_method": "credit_card",
  "payment_status": "Completed",
  "tracking_number": "TRACK123456",
  "items": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "title": "Oxford Shoes",
      "size": "9",
      "quantity": 2,
      "unit_price": 299.99,
      "subtotal": 599.98
    }
  ],
  "created_at": "2024-01-01T12:00:00"
}
```

---

### Track Order
Get order tracking information.

**Endpoint**: `GET /api/orders/<order_id>/track`

**Response** (200):
```json
{
  "order_number": "ORD-20240101-A1B2C3D4",
  "status": "Shipped",
  "payment_status": "Completed",
  "tracking_number": "TRACK123456",
  "updated_at": "2024-01-02T14:30:00",
  "estimated_delivery": "2024-01-05"
}
```

---

## Users Endpoints

### Get User Profile
Get authenticated user's profile.

**Endpoint**: `GET /api/users/profile`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "avatar_url": "https://...",
    "newsletter_subscribed": true,
    "promotions_enabled": true,
    "created_at": "2024-01-01T12:00:00"
  }
}
```

---

### Update User Profile
Update authenticated user's profile.

**Endpoint**: `PUT /api/users/profile`

**Headers Required**: Authorization

**Request Body** (all fields optional):
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "phone": "+9876543210",
  "avatar_url": "https://...",
  "newsletter_subscribed": false,
  "promotions_enabled": true
}
```

**Response** (200):
```json
{
  "message": "Profile updated successfully"
}
```

---

### Get Addresses
Get all saved addresses for user.

**Endpoint**: `GET /api/users/addresses`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "addresses": [
    {
      "id": "uuid",
      "first_name": "John",
      "last_name": "Doe",
      "company_name": "Acme Inc",
      "street_address": "123 Main St",
      "city": "Springfield",
      "state": "IL",
      "postal_code": "62701",
      "country": "USA",
      "phone": "+1234567890",
      "is_default": true,
      "address_type": "shipping"
    }
  ]
}
```

---

### Create Address
Add a new address.

**Endpoint**: `POST /api/users/addresses`

**Headers Required**: Authorization

**Request Body**:
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Acme Inc",
  "street_address": "123 Main St",
  "city": "Springfield",
  "state": "IL",
  "postal_code": "62701",
  "country": "USA",
  "phone": "+1234567890",
  "is_default": false,
  "address_type": "shipping"
}
```

**Response** (201):
```json
{
  "message": "Address created successfully",
  "address_id": "uuid"
}
```

---

### Update Address
Update an existing address.

**Endpoint**: `PUT /api/users/addresses/<address_id>`

**Headers Required**: Authorization

**Request Body** (same as Create Address)

**Response** (200):
```json
{
  "message": "Address updated successfully"
}
```

---

### Delete Address
Delete an address.

**Endpoint**: `DELETE /api/users/addresses/<address_id>`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "message": "Address deleted successfully"
}
```

---

### Get Wishlist
Get user's wishlist items.

**Endpoint**: `GET /api/users/wishlist`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "wishlist": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "title": "Oxford Shoes",
      "price": 299.99,
      "rating": 4.5
    }
  ]
}
```

---

### Add to Wishlist
Add product to wishlist.

**Endpoint**: `POST /api/users/wishlist`

**Headers Required**: Authorization

**Request Body**:
```json
{
  "product_id": "uuid"
}
```

**Response** (201):
```json
{
  "message": "Added to wishlist",
  "item_id": "uuid"
}
```

---

### Remove from Wishlist
Remove product from wishlist.

**Endpoint**: `DELETE /api/users/wishlist/<product_id>`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "message": "Removed from wishlist"
}
```

---

## Reviews Endpoints

### Get Product Reviews
Get reviews for a product.

**Endpoint**: `GET /api/reviews`

**Query Parameters**:
- `product_id` (string, required) - Product ID
- `page` (int, default: 1)
- `limit` (int, default: 10)

**Response** (200):
```json
{
  "reviews": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "rating": 5,
      "title": "Excellent shoes!",
      "comment": "Very comfortable and well-made...",
      "is_verified_purchase": true,
      "helpful_count": 15,
      "unhelpful_count": 2,
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 42,
    "pages": 5
  }
}
```

---

### Create Review
Create a product review.

**Endpoint**: `POST /api/reviews`

**Headers Required**: Authorization

**Request Body**:
```json
{
  "product_id": "uuid",
  "rating": 5,
  "title": "Excellent shoes!",
  "comment": "These shoes are very comfortable and well-made. Highly recommended!"
}
```

**Response** (201):
```json
{
  "message": "Review created successfully",
  "review_id": "uuid"
}
```

---

### Delete Review
Delete a review.

**Endpoint**: `DELETE /api/reviews/<review_id>`

**Headers Required**: Authorization

**Response** (200):
```json
{
  "message": "Review deleted successfully"
}
```

---

### Mark Helpful
Mark a review as helpful.

**Endpoint**: `POST /api/reviews/<review_id>/helpful`

**Response** (200):
```json
{
  "message": "Marked as helpful"
}
```

---

### Mark Unhelpful
Mark a review as unhelpful.

**Endpoint**: `POST /api/reviews/<review_id>/unhelpful`

**Response** (200):
```json
{
  "message": "Marked as unhelpful"
}
```

---

## Coupons Endpoints

### Get Active Coupons
Get all active coupons.

**Endpoint**: `GET /api/coupons`

**Response** (200):
```json
{
  "coupons": [
    {
      "id": "uuid",
      "code": "SAVE10",
      "discount_type": "percentage",
      "discount_value": 10.0,
      "description": "Save 10% on orders",
      "minimum_purchase": 50.0,
      "max_uses": 1000,
      "uses_count": 234,
      "valid_from": "2024-01-01T00:00:00",
      "valid_until": "2024-12-31T23:59:59"
    }
  ]
}
```

---

### Validate Coupon
Validate a coupon code.

**Endpoint**: `POST /api/coupons/validate`

**Request Body**:
```json
{
  "code": "SAVE10",
  "cart_total": 150.00
}
```

**Response** (200):
```json
{
  "valid": true,
  "coupon_id": "uuid",
  "code": "SAVE10",
  "discount_type": "percentage",
  "discount_value": 10.0,
  "discount_amount": 15.00,
  "description": "Save 10% on orders"
}
```

---

## Blog Endpoints

### Get Blog Posts
Get list of published blog posts.

**Endpoint**: `GET /api/blog`

**Query Parameters**:
- `page` (int, default: 1)
- `limit` (int, default: 10)
- `category` (string) - Filter by category
- `search` (string) - Search by title or content

**Response** (200):
```json
{
  "posts": [
    {
      "id": "uuid",
      "title": "Care Guide for Leather Shoes",
      "slug": "care-guide-leather-shoes",
      "category": "Tips",
      "excerpt": "Learn how to properly care for your leather shoes...",
      "featured_image": "https://...",
      "author": "John Smith",
      "view_count": 1250,
      "published_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-05T14:30:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 28,
    "pages": 3
  }
}
```

---

### Get Blog Post
Get detailed blog post content.

**Endpoint**: `GET /api/blog/<post_id>`

**Response** (200):
```json
{
  "id": "uuid",
  "title": "Care Guide for Leather Shoes",
  "slug": "care-guide-leather-shoes",
  "category": "Tips",
  "excerpt": "Learn how to properly care...",
  "content": "Full HTML content of the blog post...",
  "featured_image": "https://...",
  "author": "John Smith",
  "view_count": 1251,
  "published_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-05T14:30:00"
}
```

---

### Get Blog Post by Slug
Get blog post using URL-friendly slug.

**Endpoint**: `GET /api/blog/by-slug/<slug>`

**Response**: Same as Get Blog Post

---

### Get Related Posts
Get related blog posts from same category.

**Endpoint**: `GET /api/blog/related/<post_id>`

**Response** (200):
```json
{
  "related_posts": [
    {
      "id": "uuid",
      "title": "Shoe Repair Tips",
      "slug": "shoe-repair-tips",
      "excerpt": "Common shoe repair methods...",
      "featured_image": "https://...",
      "view_count": 890
    }
  ]
}
```

---

## Store Endpoints

### Get All Stores
Get all store locations.

**Endpoint**: `GET /api/stores`

**Response** (200):
```json
{
  "stores": [
    {
      "id": "uuid",
      "store_name": "Harrison Bull - Downtown",
      "email": "downtown@harrisonbull.com",
      "phone": "+1-555-0100",
      "address": {
        "street": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA"
      },
      "coordinates": {
        "latitude": 40.7128,
        "longitude": -74.0060
      }
    }
  ]
}
```

---

### Get Store Details
Get store information with hours.

**Endpoint**: `GET /api/stores/<store_id>`

**Response** (200):
```json
{
  "id": "uuid",
  "store_name": "Harrison Bull - Downtown",
  "email": "downtown@harrisonbull.com",
  "phone": "+1-555-0100",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "USA"
  },
  "coordinates": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "description": "Our flagship store...",
  "hours": {
    "Monday": {
      "opening_time": "10:00:00",
      "closing_time": "18:00:00",
      "is_closed": false
    },
    "Sunday": {
      "opening_time": null,
      "closing_time": null,
      "is_closed": true
    }
  }
}
```

---

### Search Stores
Search stores by city or state.

**Endpoint**: `GET /api/stores/search`

**Query Parameters**:
- `q` (string, required) - Search query (minimum 2 characters)

**Response** (200):
```json
{
  "results": [
    {
      "id": "uuid",
      "store_name": "Harrison Bull - Downtown",
      "city": "New York",
      "state": "NY",
      "phone": "+1-555-0100"
    }
  ]
}
```

---

### Get Nearest Stores
Find stores nearest to coordinates.

**Endpoint**: `GET /api/stores/nearest`

**Query Parameters**:
- `latitude` (float, required)
- `longitude` (float, required)
- `limit` (int, default: 5)

**Response** (200):
```json
{
  "stores": [
    {
      "id": "uuid",
      "store_name": "Harrison Bull - Downtown",
      "city": "New York",
      "state": "NY",
      "phone": "+1-555-0100",
      "coordinates": {
        "latitude": 40.7128,
        "longitude": -74.0060
      },
      "distance_miles": 2.5
    }
  ]
}
```

---

## Admin Endpoints

All admin endpoints require JWT authentication with `is_admin: true`

### Dashboard Statistics
Get admin dashboard statistics.

**Endpoint**: `GET /api/admin/dashboard`

**Headers Required**: Authorization (admin user)

**Response** (200):
```json
{
  "total_users": 1250,
  "total_orders": 3450,
  "total_products": 85,
  "total_revenue": 287350.50,
  "pending_orders": 23
}
```

---

### Create Product
Create a new product.

**Endpoint**: `POST /api/admin/products`

**Headers Required**: Authorization (admin user)

**Request Body**:
```json
{
  "title": "New Oxford Shoes",
  "price": 299.99,
  "category_id": "uuid",
  "slug": "new-oxford-shoes",
  "sku": "NOS-001",
  "original_price": 399.99,
  "short_description": "Premium new oxfords",
  "description": "Detailed description...",
  "color": "Black"
}
```

**Response** (201):
```json
{
  "message": "Product created successfully",
  "product_id": "uuid"
}
```

---

### Update Product
Update product information.

**Endpoint**: `PUT /api/admin/products/<product_id>`

**Headers Required**: Authorization (admin user)

**Request Body** (all fields optional):
```json
{
  "title": "Updated Title",
  "price": 349.99,
  "is_best_seller": true
}
```

**Response** (200):
```json
{
  "message": "Product updated successfully"
}
```

---

### Delete Product
Delete (soft delete) a product.

**Endpoint**: `DELETE /api/admin/products/<product_id>`

**Headers Required**: Authorization (admin user)

**Response** (200):
```json
{
  "message": "Product deleted successfully"
}
```

---

### Get All Orders
Get all orders (admin view).

**Endpoint**: `GET /api/admin/orders`

**Headers Required**: Authorization (admin user)

**Query Parameters**:
- `page` (int, default: 1)
- `limit` (int, default: 10)
- `status` (string) - Filter by status

**Response** (200):
```json
{
  "orders": [
    {
      "id": "uuid",
      "order_number": "ORD-20240101-A1B2C3D4",
      "customer_email": "user@example.com",
      "total": 612.97,
      "status": "Pending",
      "payment_status": "Completed",
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 3450,
    "pages": 345
  }
}
```

---

### Update Order Status
Update order status.

**Endpoint**: `PUT /api/admin/orders/<order_id>/status`

**Headers Required**: Authorization (admin user)

**Request Body**:
```json
{
  "status": "Shipped"
}
```

**Valid Statuses**: `Pending`, `Processing`, `Shipped`, `Delivered`, `Cancelled`

**Response** (200):
```json
{
  "message": "Order status updated successfully"
}
```

---

### Create Coupon
Create a new coupon.

**Endpoint**: `POST /api/admin/coupons`

**Headers Required**: Authorization (admin user)

**Request Body**:
```json
{
  "code": "HOLIDAY20",
  "discount_type": "percentage",
  "discount_value": 20,
  "description": "Holiday 20% off",
  "minimum_purchase": 100,
  "max_uses": 500,
  "valid_from": "2024-12-01T00:00:00",
  "valid_until": "2024-12-31T23:59:59"
}
```

**Response** (201):
```json
{
  "message": "Coupon created successfully",
  "coupon_id": "uuid"
}
```

---

### Sales Analytics
Get sales analytics.

**Endpoint**: `GET /api/admin/analytics/sales`

**Headers Required**: Authorization (admin user)

**Query Parameters**:
- `period` (string, default: `monthly`) - Time period filter

**Response** (200):
```json
{
  "sales": [
    {
      "date": "2024-01-15T00:00:00",
      "orders": 45,
      "revenue": 13487.50
    }
  ]
}
```

---

# Error Codes

| Code | Description |
|------|-------------|
| `INVALID_EMAIL` | Email format is invalid |
| `EMAIL_EXISTS` | Email is already registered |
| `INVALID_PASSWORD` | Password doesn't meet requirements |
| `INVALID_CREDENTIALS` | Email or password is incorrect |
| `EXPIRED_TOKEN` | JWT token has expired |
| `INVALID_TOKEN` | JWT token is invalid |
| `UNAUTHORIZED` | User is not authenticated |
| `FORBIDDEN` | User doesn't have permission |
| `NOT_FOUND` | Resource doesn't exist |
| `VALIDATION_ERROR` | Input validation failed |
| `SERVER_ERROR` | Internal server error |

---

# Rate Limiting

Currently not implemented but planned for future versions.

---

# Changelog

## Version 1.0.0 (2024-01-01)
- Initial release
- Core API endpoints
- JWT authentication
- Product catalog
- Order management
- User profiles
- Reviews and ratings
- Blog posts
- Store locator
- Admin dashboard
