# Harrison Bull Backend API

A comprehensive Flask REST API for the Harrison Bull e-commerce platform, featuring JWT authentication, product management, order processing, and admin dashboard.

## Technology Stack

- **Framework**: Flask 3.0.0 with SQLAlchemy ORM
- **Database**: PostgreSQL (hosted on Render)
- **Authentication**: JWT tokens with Flask-JWT-Extended
- **Security**: bcrypt for password hashing
- **Server**: Gunicorn WSGI server
- **Deployment**: Render Web Service

## Project Structure

```
backend/
├── endpoints/              # API endpoint modules
│   ├── auth.py            # Authentication & user registration
│   ├── products.py        # Product catalog & search
│   ├── orders.py          # Order management
│   ├── users.py           # User profiles & addresses
│   ├── reviews.py         # Product reviews
│   ├── coupons.py         # Coupon management
│   ├── blog.py            # Blog posts
│   ├── stores.py          # Store locations
│   └── admin.py           # Admin dashboard
├── database/
│   ├── schema.sql         # Database schema
│   ├── seed_data.sql      # Sample data
│   └── RENDER_SETUP.md    # Render PostgreSQL setup guide
├── app.py                 # Flask application factory
├── config.py              # Configuration management
├── extensions.py          # Flask extensions initialization
├── wsgi.py                # WSGI entry point for Render
├── requirements.txt       # Python dependencies
├── Procfile               # Render deployment configuration
├── .env.example           # Environment variables template
├── architecture.md        # System architecture documentation
└── README.md              # This file
```

## Features

### Authentication
- User registration with email validation
- JWT-based login
- Password hashing with bcrypt
- Password reset functionality
- Admin access control

### Products
- Product listing with pagination & filtering
- Product search by name and description
- Category browsing
- Product details with images and specifications
- Best sellers and featured products

### Orders
- Order creation with cart items
- Order history for logged-in users
- Order status tracking
- Multiple payment methods support
- Coupon application to orders

### User Management
- User profile management
- Multiple shipping addresses
- Wishlist functionality
- Order history
- Newsletter preferences

### Reviews
- Product reviews with ratings
- Verified purchase badges
- Helpful/unhelpful votes
- Average rating calculations
- Automatic product rating updates

### Coupons
- Coupon validation
- Discount types (percentage and fixed)
- Usage limits and date ranges
- Minimum purchase requirements

### Blog
- Blog post publishing
- Category-based browsing
- Search functionality
- View count tracking
- Related posts suggestions

### Store Locations
- Store information and hours
- Geolocation search
- Nearest store finder
- Multiple store support

### Admin Dashboard
- System statistics
- Product management (CRUD)
- Order management and status updates
- User management
- Coupon creation and management
- Sales analytics

## Setup and Installation

### 1. Prerequisites
- Python 3.8+
- PostgreSQL database (create on Render)
- pip package manager

### 2. Local Development Setup

```bash
# Clone the repository
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
# See database/RENDER_SETUP.md for instructions
```

### 3. Running Locally

```bash
# Start the Flask development server
python -m flask run

# Or using the WSGI server
gunicorn wsgi:app
```

The API will be available at `http://localhost:5000`

### 4. Render Deployment

#### Step 1: Create PostgreSQL Database on Render
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "PostgreSQL"
3. Configure database settings
4. Copy the connection string

#### Step 2: Create Web Service on Render
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: harrison-bull-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`

#### Step 3: Set Environment Variables
In Render dashboard, add these environment variables:
```
FLASK_ENV=production
JWT_SECRET=<generate-a-secure-random-string>
DATABASE_URL=<paste-PostgreSQL-connection-string>
FRONTEND_URL=<your-frontend-url>
```

#### Step 4: Initialize Database
```bash
# Connect to Render PostgreSQL via psql
psql <DATABASE_URL>

# Load schema
\i database/schema.sql

# Load seed data (optional)
\i database/seed_data.sql
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user (requires JWT)
- `POST /api/auth/logout` - Logout user
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password

### Products
- `GET /api/products` - List products (paginated, filterable)
- `GET /api/products/<id>` - Get product details
- `GET /api/products/by-slug/<slug>` - Get product by slug
- `GET /api/products/search` - Search products
- `GET /api/products/categories` - Get product categories

### Orders
- `POST /api/orders` - Create new order
- `GET /api/orders` - Get user's orders (requires JWT)
- `GET /api/orders/<id>` - Get order details
- `GET /api/orders/<id>/track` - Track order status

### Users
- `GET /api/users/profile` - Get user profile (requires JWT)
- `PUT /api/users/profile` - Update user profile
- `GET /api/users/addresses` - Get saved addresses
- `POST /api/users/addresses` - Add new address
- `PUT /api/users/addresses/<id>` - Update address
- `DELETE /api/users/addresses/<id>` - Delete address
- `GET /api/users/wishlist` - Get wishlist
- `POST /api/users/wishlist` - Add to wishlist
- `DELETE /api/users/wishlist/<product_id>` - Remove from wishlist

### Reviews
- `GET /api/reviews` - Get product reviews
- `POST /api/reviews` - Create review (requires JWT)
- `DELETE /api/reviews/<id>` - Delete review (requires JWT)
- `POST /api/reviews/<id>/helpful` - Mark helpful
- `POST /api/reviews/<id>/unhelpful` - Mark unhelpful

### Coupons
- `GET /api/coupons` - Get active coupons
- `POST /api/coupons/validate` - Validate coupon code
- `POST /api/coupons/<id>/apply` - Apply coupon

### Blog
- `GET /api/blog` - Get blog posts (paginated)
- `GET /api/blog/<id>` - Get single blog post
- `GET /api/blog/by-slug/<slug>` - Get post by slug
- `GET /api/blog/categories` - Get blog categories
- `GET /api/blog/related/<id>` - Get related posts

### Stores
- `GET /api/stores` - Get all store locations
- `GET /api/stores/<id>` - Get store details and hours
- `GET /api/stores/search` - Search stores by city/state
- `GET /api/stores/nearest` - Find nearest stores by coordinates

### Admin (requires admin authorization)
- `GET /api/admin/dashboard` - Dashboard statistics
- `POST /api/admin/products` - Create product
- `PUT /api/admin/products/<id>` - Update product
- `DELETE /api/admin/products/<id>` - Delete product
- `GET /api/admin/orders` - Get all orders
- `PUT /api/admin/orders/<id>/status` - Update order status
- `GET /api/admin/users` - Get all users
- `PUT /api/admin/users/<id>/status` - Activate/deactivate user
- `POST /api/admin/coupons` - Create coupon
- `GET /api/admin/analytics/sales` - Sales analytics

## Environment Variables

Create a `.env` file with the following variables (see `.env.example`):

```
FLASK_ENV=production
FLASK_APP=wsgi.py
DEBUG=False
API_PORT=5000
JWT_SECRET=your-secure-secret-key
DATABASE_URL=postgresql://user:password@host:port/dbname
FRONTEND_URL=https://your-frontend-domain.com
```

## Database Schema

The database includes 18 tables:
- `users` - User accounts
- `addresses` - Shipping/billing addresses
- `categories` - Product categories
- `products` - Product information
- `product_specifications` - Detailed product specs
- `product_images` - Product photos
- `product_sizes` - Available sizes
- `cart_items` - Shopping cart items
- `orders` - Order records
- `order_items` - Items in orders
- `coupons` - Discount coupons
- `promotional_banners` - Marketing banners
- `product_reviews` - Customer reviews
- `wishlist_items` - Wishlist entries
- `blog_posts` - Blog articles
- `store_locations` - Physical store info
- `store_hours` - Store operating hours
- `notifications` - User notifications
- `audit_logs` - System activity logs

See `database/schema.sql` for complete schema details.

## Security Considerations

1. **JWT Secret**: Generate a strong random secret for JWT signing
2. **Password Hashing**: All passwords are bcrypt hashed
3. **CORS**: Frontend URL must be whitelisted
4. **SQL Injection**: All queries use parameterized statements
5. **Admin Authorization**: All admin endpoints require JWT with admin flag

## Performance Features

- Connection pooling (pool_size=10, pool_recycle=3600)
- Database query optimization with proper indexes
- Pagination on large result sets
- Soft deletes for data preservation
- Caching-friendly architecture

## Monitoring and Logging

- Activity logging for all user actions
- Audit logs for admin operations
- Error logging with traceback
- Request logging for debugging

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL is correct
- Check Render PostgreSQL firewall settings
- Ensure schema is loaded

### JWT Token Errors
- Verify JWT_SECRET is set correctly
- Check token hasn't expired (expires in 24 hours)
- Ensure Authorization header is in format: `Bearer <token>`

### CORS Errors
- Verify FRONTEND_URL environment variable
- Check request origin matches FRONTEND_URL
- Ensure credentials are handled correctly

## Future Enhancements

- Email notification system
- Payment gateway integration (Stripe, PayPal)
- Inventory management
- Advanced analytics dashboard
- Product recommendations engine
- Wishlist sharing
- Social login integration
- Rate limiting and throttling
- API versioning

## Support

For issues or questions, please refer to:
- `database/RENDER_SETUP.md` - Database setup guide
- `architecture.md` - System architecture
- Flask documentation: https://flask.palletsprojects.com
- SQLAlchemy documentation: https://www.sqlalchemy.org

## License

Proprietary - Harrison Bull
