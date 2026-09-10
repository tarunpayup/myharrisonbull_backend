# Render PostgreSQL Setup Guide

Complete step-by-step guide for setting up PostgreSQL database on Render.com for Harrison Bull e-commerce platform.

## Prerequisites

- Render account (free at https://render.com/)
- `psql` command-line tool installed locally
- Internet connection

## Step 1: Create Render Account

1. Go to [Render.com](https://render.com/)
2. Click **Sign Up**
3. Choose signup method (Google, GitHub, or Email)
4. Verify email if needed
5. You're ready to create databases!

## Step 2: Create PostgreSQL Database

### Via Render Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** (top right)
3. Select **PostgreSQL**
4. Fill in database details:
   - **Name:** `harrison-bull-db` (or your preference)
   - **Database:** `harrison_bull_db` (matches schema)
   - **User:** (auto-generated, e.g., `user`)
   - **Region:** Select closest to your users (e.g., US-East, EU-Frankfurt)
   - **PostgreSQL Version:** Use latest (15+)
   - **Plan:** 
     - **Free:** Good for development/testing (90 GB storage, 1 connection)
     - **Standard:** Production ready (more connections, dedicated CPU)

5. Click **Create Database**
6. Wait 2-3 minutes for provisioning (watch the status)

### Database is Ready When:
- Status shows green **"Available"**
- You see connection details section

## Step 3: Get Connection Details

Once database is created:

1. Click on your database name in dashboard
2. Scroll to **"Connections"** section
3. You'll see:
   - **External Database URL:** `postgresql://user:password@host.render.com:5432/harrison_bull_db`
   - **PSQL Command:** Ready-to-use connection command
   - **Hostname, Username, Password, Database:** Individual values

### Copy Connection Details
```
Format: postgresql://username:password@hostname:5432/dbname

Example:
postgresql://harrisonbull_user:abc123def456@dpg-xyz123.render.com:5432/harrison_bull_db
```

**Keep these safe!** You'll need them for:
- Loading database schema
- Backend application `.env` file
- pgAdmin connections

## Step 4: Install PostgreSQL Client (psql)

You need `psql` to load the schema. Install if not already done:

### macOS
```bash
brew install postgresql
```

### Ubuntu/Debian
```bash
sudo apt-get install postgresql-client
```

### Windows
1. Download [PostgreSQL](https://www.postgresql.org/download/windows/)
2. During install, uncheck "Stack Builder"
3. Remember the password you set
4. Add to PATH: `C:\Program Files\PostgreSQL\15\bin`

### Verify Installation
```bash
psql --version
# Output: psql (PostgreSQL) 15.x
```

## Step 5: Load Database Schema

Now load the Harrison Bull schema into your Render database.

### Option A: Using External Database URL (Easiest)

```bash
# From the database directory
cd backend/database

# Load schema
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" -f schema.sql

# Enter password when prompted (or it's included in URL)
```

### Option B: Using Individual Connection Parameters

```bash
cd backend/database

psql \
  -h host.render.com \
  -U user \
  -d harrison_bull_db \
  -f schema.sql
```

When prompted, enter the password from Render.

### Option C: Using PGPASSWORD Environment Variable

```bash
# macOS/Linux
export PGPASSWORD='your_password_from_render'
psql -h host.render.com -U user -d harrison_bull_db -f schema.sql

# Windows (PowerShell)
$env:PGPASSWORD='your_password_from_render'
psql -h host.render.com -U user -d harrison_bull_db -f schema.sql
```

### Troubleshooting Schema Load

**Error: "could not translate host name"**
- ❌ Hostname is wrong (not from Render)
- ✅ Copy exact hostname from Render dashboard

**Error: "FATAL: no pg_hba.conf entry"**
- ❌ Password is wrong
- ✅ Copy password exactly from Render dashboard

**Error: "Database does not exist"**
- ❌ Database name is wrong
- ✅ Should be `harrison_bull_db` (exact match)

**Timeout errors**
- Wait a few minutes after creating database
- Render may still be initializing
- Try again in 2-3 minutes

## Step 6: Verify Schema Loaded

Connect to your database and check tables:

```bash
# Connect to database
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db"

# Inside psql, run:
\dt

# You should see 18 tables:
# - users
# - addresses
# - categories
# - products
# - product_images
# - product_specifications
# - product_sizes
# - cart_items
# - orders
# - order_items
# - coupons
# - promotional_banners
# - product_reviews
# - wishlist_items
# - blog_posts
# - store_locations
# - store_hours
# - notifications
# (plus audit_logs)

# Check record count
SELECT COUNT(*) FROM products;
# Should return: 4 (or 0 if you skipped seed data)

# Exit psql
\q
```

## Step 7: Load Sample Data (Optional)

For development/testing, load sample data:

```bash
cd backend/database

# Load seed data
psql "postgresql://user:password@host.render.com:5432/harrison_bull_db" -f seed_data.sql
```

This adds:
- Admin user (admin@harrisonbull.com)
- 2 test users
- 4 sample products
- 7 categories
- 3 promotional banners
- 3 coupons
- 4 product reviews
- 4 store locations
- 2 blog posts

## Step 8: Configure Backend Application

### 1. Create `.env` File

```bash
cp database/.env.example .env
```

### 2. Edit `.env` with Render Connection

```env
# From Render Dashboard - Connection Details
DATABASE_URL=postgresql://user:password@host.render.com:5432/harrison_bull_db

# Alternative - individual settings
DATABASE_HOST=host.render.com
DATABASE_PORT=5432
DATABASE_NAME=harrison_bull_db
DATABASE_USER=user
DATABASE_PASSWORD=your_password
```

### 3. Set Up Connection Pooling

For production, enable connection pooling:

```env
# Optional: Use Render's PgBouncer
DATABASE_URL=postgresql://user:password@host.render.com:5432/harrison_bull_db?sslmode=require
```

Render provides PgBouncer for higher connection limits.

## Step 9: Deploy to Render Web Service

### 1. Push Code to GitHub

```bash
git add .
git commit -m "Add database configuration for Render"
git push origin main
```

### 2. Create Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Web Service**
3. Connect GitHub repository
4. Configure:
   - **Name:** `harrison-bull-api` (or your choice)
   - **Environment:** Node (or your language)
   - **Build Command:** `npm run build` (or your build command)
   - **Start Command:** `npm start`
   - **Plan:** Free or Starter

### 3. Add Environment Variables

In Web Service settings:
1. Click **Environment**
2. Add from `.env`:
   - `DATABASE_URL`
   - `API_PORT`
   - `JWT_SECRET`
   - Other variables from `.env`

### 4. Deploy

1. Click **Create Web Service**
2. Render will automatically:
   - Clone your repository
   - Build application
   - Start your service
3. Get your live URL: `https://your-service-name.onrender.com`

## Step 10: Test API Connection

```bash
# Test API is running
curl https://your-service-name.onrender.com/health

# Test database connection from API
curl https://your-service-name.onrender.com/api/products
```

## Monitoring & Maintenance

### Check Database Status

1. Render Dashboard → Your PostgreSQL instance
2. Check **Status** indicator (should be green)
3. View metrics:
   - **Connections:** Current active connections
   - **Queries/sec:** Database activity
   - **CPU/Memory:** Resource usage

### View Database Logs

1. Database page → **Logs** tab
2. See real-time database activity
3. Monitor for errors or slow queries

### Manage Backups

1. Database page → **Backups** tab
2. View automatic daily backups
3. Restore from backup if needed:
   - Click **Restore** next to backup date
   - Choose retention period
   - Click **Restore**

### Scale Resources (if needed)

1. Database page → **Plan**
2. Upgrade to:
   - More storage
   - Dedicated CPU
   - Higher connection limits
   - Longer backup retention

## Common Issues & Solutions

### Issue: "too many connections"
**Solution:** 
- Upgrade to paid plan for more connections
- Use PgBouncer connection pooling
- Close unused connections in application

### Issue: "SSL certificate problem"
**Solution:**
```bash
# Use SSL mode in connection
DATABASE_URL=postgresql://user:password@host.render.com:5432/harrison_bull_db?sslmode=require
```

### Issue: High CPU/Memory usage
**Solution:**
- Optimize slow queries (see BEST_PRACTICES.md)
- Add database indexes
- Upgrade to paid plan with dedicated resources

### Issue: Backup not working
**Solution:**
- Free plan: Only 7-day backup retention
- Upgrade to paid for longer retention
- Manual backup: `pg_dump` to file

## Security Best Practices

1. **Never commit `.env` to Git**
   ```bash
   echo ".env" >> .gitignore
   git rm --cached .env
   ```

2. **Use strong passwords** for database user

3. **Enable SSL connections**
   ```env
   DATABASE_URL=...?sslmode=require
   ```

4. **Rotate credentials periodically**
   - Render: Reset password in database settings

5. **Restrict access** (if using Render Pro)
   - Whitelist IP addresses
   - Use VPC for private networks

6. **Monitor backups**
   - Verify backups are happening
   - Test restore procedures

## Useful Render Documentation

- [Render Databases](https://render.com/docs/databases)
- [PostgreSQL](https://render.com/docs/postgresql)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Backups](https://render.com/docs/postgresql-backups)
- [Troubleshooting](https://render.com/docs/troubleshooting)

## Support

- **Render Support:** https://render.com/support
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **GitHub Issues:** Create issue in your repository

## Next Steps

✅ Database is now live on Render!

Continue with:
1. Build backend API endpoints (see architecture.md)
2. Implement authentication
3. Create CRUD operations
4. Deploy to Render Web Service
5. Connect frontend to live API

---

**Setup completed on:** 2026-09-10
**Database:** PostgreSQL on Render
**Status:** Ready for development & deployment
