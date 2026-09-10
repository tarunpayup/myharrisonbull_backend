# PostgreSQL Database Setup - Harrison Bull E-Commerce Platform

## Overview

This directory contains the PostgreSQL database schema and seed data for the Harrison Bull e-commerce platform. The database is designed to support a full-featured luxury shoe e-commerce application.

## Files

### 1. `schema.sql`
Complete PostgreSQL schema with all tables, relationships, constraints, and indexes.

**Tables:**
- **User Management**: `users`, `addresses`
- **Product Catalog**: `categories`, `products`, `product_specifications`, `product_images`, `product_sizes`
- **Shopping**: `cart_items`, `orders`, `order_items`
- **Promotions**: `coupons`, `promotional_banners`
- **Content**: `product_reviews`, `blog_posts`, `store_locations`, `store_hours`
- **User Features**: `wishlist_items`, `notifications`
- **Admin**: `audit_logs`

### 2. `seed_data.sql`
Sample data for development and testing, including:
- Admin and test users
- 7 product categories
- 4 sample products with images and specifications
- Promotional banners and coupons
- Product reviews
- Store locations with hours
- Blog posts

## Prerequisites

- PostgreSQL client (`psql`) installed locally
  - **macOS:** `brew install postgresql`
  - **Ubuntu/Debian:** `sudo apt-get install postgresql-client`
  - **Windows:** [Download PostgreSQL](https://www.postgresql.org/download/windows/)
- Render account ([Create free account](https://render.com/))
- Text editor for SQL files

## Quick Start (Render PostgreSQL)

### 1. Create PostgreSQL Database on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"PostgreSQL"**
3. Fill in details:
   - **Name:** harrison_bull_db (or your choice)
   - **Database:** harrison_bull_db
   - **User:** (auto-generated)
   - **Region:** Choose closest to your users
   - **Plan:** Free or paid (as needed)
4. Click **"Create Database"**
5. Wait 2-3 minutes for provisioning
6. Copy the **External Database URL** from the connection details

### 2. Load Schema into Render Database

Get your connection details from Render and run:

```bash
# Using the External Database URL from Render
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" -f schema.sql
```

Or use individual parameters:
```bash
psql -h host.render.com -U user -d harrison_bull_db -f schema.sql
```

When prompted, paste the password from Render.

### 3. Load Seed Data (Optional, for development only)

```bash
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" -f seed_data.sql
```

### 4. Verify Installation

```bash
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db"

# Inside psql:
# Check tables
\dt

# Check table structure
\d products

# Count records
SELECT COUNT(*) FROM products;
```

## Database Connection

### Connection String (Render Format)
```
postgresql://user:password@host.render.com:5432/harrison_bull_db
```

### Get Your Render Connection Details

1. Log in to [Render Dashboard](https://dashboard.render.com/)
2. Click on your PostgreSQL database instance
3. Scroll to **"Connections"** section
4. Copy **"External Database URL"** (includes all credentials)
5. Use this in your `.env` file

### Environment Variables (.env)
```
# Single connection string (Render format)
DATABASE_URL=postgresql://user:password@host.render.com:5432/harrison_bull_db

# Alternative: Split credentials
DATABASE_HOST=host.render.com
DATABASE_PORT=5432
DATABASE_NAME=harrison_bull_db
DATABASE_USER=user
DATABASE_PASSWORD=your_password
```

### Render Dashboard Access

- **Dashboard:** https://dashboard.render.com/
- **Docs:** https://render.com/docs/databases
- **Connection Status:** Check "Connections" tab in database settings

## Schema Details

### Users Table
- Stores user accounts, credentials, and preferences
- Email is unique for login
- Tracks admin status and account activity
- Soft deletes via `deleted_at` timestamp

### Products Table
- Central product catalog for shoes
- Linked to categories
- Tracks pricing, discounts, inventory status
- Includes ratings and review counts (denormalized for performance)

### Orders Table
- Complete order history with status tracking
- Supports both registered users and guest checkout
- Stores shipping and billing addresses
- Tracks payment status separately from order status

### Product Reviews
- Product ratings and customer feedback
- Includes moderation (is_approved flag)
- Tracks verification of purchase

### Wishlists
- User-specific saved items
- Composite unique constraint prevents duplicates

### Blog Posts & Store Locations
- Content management for educational and store information
- Store hours normalized in separate table for flexibility

## Key Design Decisions

### 1. UUID Primary Keys
All tables use `UUID` (gen_random_uuid()) for primary keys:
- Better for distributed systems
- Globally unique identifiers
- Reduces enumeration attacks

### 2. Soft Deletes
Users and Products support soft deletes via `deleted_at`:
- Preserves referential integrity
- Allows data recovery
- Maintains audit trail

### 3. Denormalization
Some values are denormalized for performance:
- `rating` and `reviews_count` in products table
- `product_title` in order_items (preserves historical data)

### 4. Composite Keys
Some tables use composite unique constraints:
- `product_sizes`: unique(product_id, size)
- `wishlist_items`: unique(user_id, product_id)

### 5. Timestamps
All tables include `created_at` and `updated_at`:
- Useful for pagination, filtering, sorting
- Automatic defaults via CURRENT_TIMESTAMP
- Indexed for performance on frequently queried ranges

## Indexes

Indexes are created on:
- Foreign key columns (join performance)
- Commonly filtered columns (status, is_active, category_id)
- Sorting columns (created_at, display_order)
- Text search columns (email, slug)

Add more indexes based on query performance analysis.

## Data Types

### Money/Pricing
- `DECIMAL(10, 2)` for all monetary values
- Supports values up to $99,999,999.99
- More precise than FLOAT for financial data

### Text Fields
- `VARCHAR(n)` for limited-length strings (email, names, URLs)
- `TEXT` for unlimited content (descriptions, comments)

### Relationships
- `UUID` references for all foreign keys
- `ON DELETE CASCADE` for dependent records (reviews delete with products)
- `ON DELETE SET NULL` for optional relationships (orders can exist without users)

## Migration Strategy

For production deployments, implement versioned migrations:

```
migrations/
  001_initial_schema.sql
  002_add_column_x.sql
  003_create_index_y.sql
```

Use a migration tool like:
- Flyway
- Liquibase
- node-migrate
- db-migrate

Example migration tool command:
```bash
# Apply migrations
migrate -path ./database/migrations -database postgresql://... up

# Rollback
migrate -path ./database/migrations -database postgresql://... down
```

## Backup & Restore (Render)

### Automatic Backups
Render automatically backs up your database:
- **Free tier:** 7-day backups
- **Paid tier:** 30-day backups
- Access via Render Dashboard → Database → "Backups" tab

### Manual Backup
```bash
# Backup entire database
pg_dump "postgresql://user:password@host.render.com:5432/harrison_bull_db" > backup_$(date +%Y%m%d).sql

# Backup specific table
pg_dump "postgresql://user:password@host.render.com:5432/harrison_bull_db" -t products > products_backup.sql

# Compressed backup (smaller file)
pg_dump "postgresql://user:password@host.render.com:5432/harrison_bull_db" | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Database
```bash
# Restore from backup
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" < backup_20260910.sql

# Restore from compressed backup
gunzip < backup_20260910.sql.gz | psql "postgresql://user:password@host.render.com:5432/harrison_bull_db"
```

### Render Restore from Backup
1. Go to Render Dashboard
2. Select your PostgreSQL instance
3. Click "Backups" tab
4. Click "Restore" next to desired backup
5. Choose retention period
6. Click "Restore"

## Common Queries

### Check Database Size
```sql
SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) 
FROM pg_database 
WHERE datname = 'harrison_bull_db';
```

### Find Slow Queries
Enable query logging:
```sql
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries taking > 1 second
SELECT pg_reload_conf();
```

### Analyze Query Plans
```sql
EXPLAIN ANALYZE SELECT * FROM products WHERE category_id = '...';
```

## Performance Optimization

### 1. Update Sequences
If loading large amounts of data, disable indexes during import:
```sql
ALTER TABLE products DISABLE TRIGGER ALL;
-- Load data
ALTER TABLE products ENABLE TRIGGER ALL;
```

### 2. Vacuum & Analyze
After large inserts:
```sql
VACUUM ANALYZE;
```

### 3. Connection Pooling
For production, use connection pooling:
- PgBouncer
- pgpool-II
- Built-in pooling in ORM (Sequelize, TypeORM, etc.)

## Security Considerations

1. **Strong Passwords**: Use strong password hashes (bcrypt, scrypt)
   - Seed data uses placeholder hash (demo only)
   - Never store plain text passwords

2. **SQL Injection Prevention**: Use parameterized queries
   - All backend queries should use prepared statements
   - Never concatenate user input into SQL strings

3. **Row-Level Security (RLS)**: Consider implementing PostgreSQL RLS
   ```sql
   ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
   CREATE POLICY user_orders_policy ON orders
   FOR SELECT USING (user_id = current_user_id());
   ```

4. **Audit Logging**: Use `audit_logs` table
   - Log all admin actions
   - Track data modifications
   - Enable compliance and debugging

5. **Encryption**: Sensitive fields
   - Encrypt PII (phone, addresses) in transit
   - Use HTTPS for all API connections

## Troubleshooting

### Connection Issues

**Error: "could not translate host name"**
- Verify the host from Render is correct (should end in `.render.com`)
- Check your internet connection
- Ensure firewall allows outbound connections to PostgreSQL port (5432)

```bash
# Test connection
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" -c "SELECT version();"
```

### Render-Specific Issues

**Database not starting**
1. Check Render Dashboard for service status
2. Look for error messages in database logs
3. Try restarting the database instance
4. Contact Render support

**Can't load schema files**
- Verify the connection string is correct
- Check Render dashboard shows "Available" status
- Ensure password doesn't contain special characters (URL encode if needed)
- Try connecting with `psql` first to verify credentials

**Timeout connecting from backend**
1. Verify backend has internet access to Render
2. Add firewall rule if needed
3. Increase connection timeout in application
4. Use connection pooling (PgBouncer on Render)

### Permission Errors
```sql
-- Grant privileges to your user
GRANT ALL PRIVILEGES ON DATABASE harrison_bull_db TO your_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
```

### Constraint Violations
Check foreign key relationships:
```sql
SELECT constraint_name, table_name, column_name 
FROM information_schema.key_column_usage 
WHERE table_name = 'orders';
```

### Check Render Database Status
From Render Dashboard:
1. Click on your PostgreSQL instance
2. Check **Status** indicator (should be green "Available")
3. View **Connection info** section
4. Check **Logs** tab for any errors

## Testing

### Test Data Integrity
```sql
-- Check for orphaned order items
SELECT oi.* FROM order_items oi
LEFT JOIN orders o ON oi.order_id = o.id
WHERE o.id IS NULL;

-- Verify all product sizes have valid products
SELECT ps.* FROM product_sizes ps
LEFT JOIN products p ON ps.product_id = p.id
WHERE p.id IS NULL;
```

## Next Steps

1. **Set up PostgreSQL on Render:**
   - Create free account at https://render.com/
   - Provision PostgreSQL database instance
   - Copy External Database URL

2. **Load database schema:**
   - Run `psql -f schema.sql` with Render connection string
   - Verify all 18 tables created
   - Optionally load seed data with `psql -f seed_data.sql`

3. **Configure backend application:**
   - Copy `.env.example` to `.env`
   - Paste Render DATABASE_URL
   - Set up ORM (Prisma, TypeORM, etc.)
   - Install connection pooling if using Render with many connections

4. **Deploy backend to Render:**
   - Create new Web Service on Render
   - Connect to your GitHub repository
   - Set environment variables from `.env`
   - Deploy and test API endpoints

5. **Monitor and maintain:**
   - Check Render dashboard for database health
   - Review backups regularly
   - Monitor connection usage
   - Set up alerts for high resource usage

## Render PostgreSQL Features

### Free Plan
- 90 GB storage
- Automatic daily backups (7-day retention)
- 1 concurrent connection
- Shared CPU

### Paid Plans
- More storage options (up to 4 TB)
- Longer backup retention (30 days)
- Multiple concurrent connections
- Dedicated CPU options

### Render Dashboard Features
- **Connection Info:** View all connection details
- **Logs:** Monitor database activity
- **Backups:** View and restore backups
- **Metrics:** Check CPU, memory, connections
- **Restart:** Restart database if needed

See [Render Docs](https://render.com/docs/databases) for more information.

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Best Practices Guide](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [UUID vs Serial Keys](https://www.postgresql.org/docs/current/datatype-uuid.html)

## Support

For questions or issues with the database schema, refer to:
- Architecture documentation: `../architecture.md`
- Backend API documentation (to be created)
- PostgreSQL official documentation
