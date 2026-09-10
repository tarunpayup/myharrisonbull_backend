# Database Folder Structure - Complete Overview

## Files Description

### Core Database Files

#### 1. `schema.sql` (4.5 KB)
**Purpose:** Complete PostgreSQL database schema
**Contents:**
- 18 tables with all relationships and constraints
- Comprehensive indexes for performance
- Data types and field validations
- Foreign key relationships with cascade rules

**Tables included:**
- Users & Addresses
- Products, Specifications, Images, Sizes
- Orders & Order Items
- Cart Items
- Coupons & Promotional Banners
- Reviews & Wishlist
- Blog Posts & Store Locations
- Notifications & Audit Logs

**When to use:** Load this first to create the database structure
```bash
psql -U postgres -d harrison_bull_db -f schema.sql
```

---

#### 2. `seed_data.sql` (8 KB)
**Purpose:** Sample data for development and testing
**Contents:**
- 2 Admin + 2 Test users
- 7 Product categories
- 4 Sample products with full details
- Product specifications and images
- Size inventory for each product
- Promotional banners (3)
- Discount coupons (3)
- Product reviews (4)
- Store locations (4) with operating hours
- Blog posts (2)

**When to use:** Load after schema for development environment
```bash
psql -U postgres -d harrison_bull_db -f seed_data.sql
```

**Test Users:**
- Admin: admin@harrisonbull.com (Password: admin123)
- User 1: john@example.com
- User 2: jane@example.com

---

#### 3. `README.md` (9 KB)
**Purpose:** Complete setup and usage guide
**Sections:**
- Quick start guide (5 steps)
- Database connection configuration
- Connection string format
- Environment variables setup
- Schema details for each table
- Design decisions (UUID keys, soft deletes, indexes)
- Data types explanation
- Migration strategy
- Backup & restore procedures
- Common queries
- Performance optimization tips
- Security considerations
- Troubleshooting guide
- Testing recommendations

**When to use:** Reference during setup and development

---

### Setup & Configuration Files

#### 4. `docker-compose.yml` (1.2 KB)
**Purpose:** Docker container setup for PostgreSQL + pgAdmin
**Services:**
- PostgreSQL 16 Alpine (lightweight)
- pgAdmin 4 (GUI database management)

**Features:**
- Automatic schema and seed data loading
- Health checks
- Network isolation
- Volume persistence for data

**Usage:**
```bash
docker-compose up -d          # Start containers
docker-compose down           # Stop containers
docker-compose logs postgres  # View logs
```

**Access:**
- PostgreSQL: localhost:5432
- pgAdmin: http://localhost:5050
  - Email: admin@harrisonbull.com
  - Password: admin

---

## Setup & Configuration Files

#### 4. `RENDER_SETUP.md` (12 KB)
**Purpose:** Complete step-by-step guide for Render PostgreSQL setup
**Sections:**
- Create Render account
- Provision PostgreSQL database
- Get connection details
- Install psql client
- Load database schema
- Verify installation
- Load sample data
- Configure backend application
- Deploy to Render Web Service
- Monitor and maintain
- Common issues & solutions
- Security best practices

**Usage:** Follow this guide to set up database on Render.com

---

#### 5. `.env.example` (0.8 KB)
**Purpose:** Environment variables template for Render
**Variables:**
- DATABASE_URL (Render format)
- Connection pool settings
- API configuration
- JWT settings
- Email/SMTP settings
- AWS S3 configuration
- Payment processing (Stripe)
- Logging & monitoring

**Usage:**
1. Copy to `.env`: `cp .env.example .env`
2. Update DATABASE_URL from Render
3. Load in application:
```javascript
require('dotenv').config();
const dbUrl = process.env.DATABASE_URL;
```

---

#### 6. `setup-render.sh` (3.5 KB)
**Purpose:** Interactive setup script specifically for Render database
**Options:**
1. Load schema only
2. Load schema + seed data
3. Test Render connection
4. Create .env file

**Usage:**
```bash
chmod +x setup-render.sh
./setup-render.sh

# Select option and enter Render DATABASE_URL
```

**Features:**
- Validates psql installation
- Tests Render connection
- Automatic .env creation
- Colored terminal output
- Simple and straightforward

---

### Migration Files

#### 7. `migrations/001_initial_schema.sql` (2.5 KB)
**Purpose:** First database migration
**Demonstrates:**
- Migration structure with UP and DOWN sections
- Proper SQL formatting
- Comments for clarity
- Includes users and addresses tables

**Usage for future migrations:**
1. Create `migrations/002_add_new_table.sql`
2. Use migration tool: `migrate up`
3. For rollback: `migrate down`

**Next migrations to create:**
- `002_add_products_tables.sql`
- `003_add_orders_tables.sql`
- `004_add_reviews_table.sql`
- etc.

---

### Documentation Files

#### 8. `BEST_PRACTICES.md` (6 KB)
**Purpose:** Database development guidelines and best practices
**Topics:**
- Connection management & pooling
- ORM recommendations (Prisma, TypeORM)
- Query best practices
- Using parameterized queries
- Pagination techniques
- Transaction handling
- Data integrity & validation
- Performance optimization
- Caching strategies
- Security guidelines
- Backup & recovery
- Monitoring queries
- Common pitfalls to avoid
- Testing database code

**When to use:** Reference during backend development

---

## Quick Setup Guide

### Option 1: Render (Recommended - Cloud)
```bash
cd database

# Follow RENDER_SETUP.md for step-by-step guide
# Or use automated script:
chmod +x setup-render.sh
./setup-render.sh

# Select option 1-2 to load schema/seed data
# Enter your Render DATABASE_URL when prompted
```

### Option 2: Using Render Setup Script
```bash
chmod +x setup-render.sh
./setup-render.sh

# Interactive prompts for:
# - Loading schema/seed data
# - Testing connection
# - Creating .env file
```

### Option 3: Manual Setup with psql
```bash
# 1. Create database on Render (see RENDER_SETUP.md)
# 2. Copy DATABASE_URL from Render dashboard

# 3. Load schema
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" -f schema.sql

# 4. Load seed data (optional)
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" -f seed_data.sql

# 5. Copy environment file
cp .env.example .env

# 6. Edit .env with your Render DATABASE_URL
```

---

## File Size Summary

| File | Size | Type |
|------|------|------|
| schema.sql | 15 KB | SQL |
| seed_data.sql | 22 KB | SQL |
| README.md | 12 KB | Markdown |
| RENDER_SETUP.md | 12 KB | Markdown |
| .env.example | 0.8 KB | Text |
| setup-render.sh | 3.5 KB | Shell Script |
| migrations/001_initial_schema.sql | 3 KB | SQL |
| BEST_PRACTICES.md | 8 KB | Markdown |
| INDEX.md | 8 KB | Markdown |
| **Total** | **~84 KB** | **-** |

---

## Database Statistics

### Tables: 18
- User Management: 2
- Product Catalog: 5
- Shopping: 3
- Promotions: 2
- Content: 4
- Features: 1 (wishlist)
- Admin: 1 (audit)

### Indexes: 50+
Strategic indexes on:
- Foreign keys (join performance)
- Frequently filtered columns (WHERE clauses)
- Sorting columns (ORDER BY)
- Text search (email, slug)

### Constraints: 30+
- Primary keys (UUID)
- Foreign keys (referential integrity)
- Unique constraints (email, slug)
- Check constraints (rating range, status values)

### Sample Data Records
- Users: 3
- Products: 4
- Categories: 7
- Orders: 0 (created during operations)
- Reviews: 4
- Blog Posts: 2
- Store Locations: 4

---

## Integration with Backend

### Node.js/Express Example
```javascript
// Load configuration
require('dotenv').config();

// Create connection pool
const { Pool } = require('pg');
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  idleTimeoutMillis: 30000,
});

// Use in routes
app.get('/products', async (req, res) => {
  const result = await pool.query('SELECT * FROM products LIMIT 10');
  res.json(result.rows);
});
```

### TypeScript + Prisma Example
```typescript
// prisma/schema.prisma references database schema
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// Auto-generates types from database
const products = await prisma.products.findMany();
```

---

## Monitoring & Maintenance

### Check Database Size
```bash
psql -d harrison_bull_db -c "SELECT pg_size_pretty(pg_database_size('harrison_bull_db'));"
```

### View Active Connections
```bash
psql -d harrison_bull_db -c "SELECT count(*) FROM pg_stat_activity;"
```

### Backup Database
```bash
pg_dump -d harrison_bull_db > backup_$(date +%Y%m%d).sql
```

### Restore from Backup
```bash
psql -d harrison_bull_db < backup_20260910.sql
```

---

## Troubleshooting

### Database Won't Start (Docker)
```bash
# Check logs
docker-compose logs postgres

# Restart
docker-compose down
docker-compose up -d
```

### Can't Connect
```bash
# Test connection
psql -h localhost -U harrison_bull -d harrison_bull_db

# Check PostgreSQL is running
ps aux | grep postgres
```

### Permission Errors
```bash
# Grant privileges
psql -U postgres -c "GRANT ALL ON DATABASE harrison_bull_db TO harrison_bull;"
```

---

## Next Steps

1. **Create PostgreSQL on Render:**
   - Follow RENDER_SETUP.md for detailed instructions
   - Or run `setup-render.sh` for interactive setup
   - Takes 2-3 minutes

2. **Verify database setup:**
   - Test connection: `psql "postgresql://..." -c "\dt"`
   - Should show 18 tables
   - Optionally load seed data

3. **Create .env file:**
   - `cp .env.example .env`
   - Paste Render DATABASE_URL
   - Set other variables (JWT, email, etc.)

4. **Build backend API:**
   - Set up Node.js/Express or framework of choice
   - Implement ORM (Prisma recommended)
   - Follow BEST_PRACTICES.md
   - Create API endpoints from architecture.md

5. **Deploy to Render Web Service:**
   - Push code to GitHub
   - Create new Web Service on Render
   - Connect repository
   - Set environment variables
   - Deploy

---

**Status:** ✅ Database setup prepared for Render
**Last Updated:** 2026-09-10
