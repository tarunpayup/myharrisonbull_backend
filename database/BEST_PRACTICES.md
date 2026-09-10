# Database Best Practices & Guidelines

## Connection Management

### 1. Use Connection Pooling
Always use connection pooling in production to avoid connection exhaustion:

```javascript
// Node.js with node-postgres (pg)
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DATABASE_USER,
  password: process.env.DATABASE_PASSWORD,
  host: process.env.DATABASE_HOST,
  port: process.env.DATABASE_PORT,
  database: process.env.DATABASE_NAME,
  max: 10,              // Max connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Use pool
const result = await pool.query('SELECT * FROM products WHERE id = $1', [productId]);
```

### 2. Use ORM for Type Safety
Recommended ORMs for Node.js:
- **Prisma** (Recommended - great TypeScript support)
- **TypeORM** (More control)
- **Sequelize** (Popular and mature)
- **Knex.js** (Query builder)

```javascript
// Prisma example
const product = await prisma.products.findUnique({
  where: { id: productId },
  include: {
    specifications: true,
    images: true,
    sizes: true,
  },
});
```

## Query Best Practices

### 1. Use Parameterized Queries (Prepared Statements)
**✅ CORRECT:**
```sql
SELECT * FROM users WHERE email = $1 AND is_active = $2
-- Parameters: [userEmail, true]
```

**❌ WRONG (SQL Injection Risk):**
```javascript
// Never do this!
const query = `SELECT * FROM users WHERE email = '${userEmail}'`;
```

### 2. Fetch Only Required Columns
**✅ CORRECT:**
```sql
SELECT id, name, price FROM products WHERE category_id = $1
```

**❌ WRONG:**
```sql
SELECT * FROM products WHERE category_id = $1
```

### 3. Use Proper Joins
**✅ CORRECT:**
```sql
SELECT p.id, p.title, p.price, ps.welt_type
FROM products p
LEFT JOIN product_specifications ps ON p.id = ps.product_id
WHERE p.category_id = $1
LIMIT 50;
```

### 4. Index Usage
Create indexes on:
- Columns used in WHERE clauses
- Foreign key columns
- Columns used in ORDER BY
- Columns used in GROUP BY

Check query plans:
```sql
EXPLAIN ANALYZE SELECT * FROM products WHERE category_id = $1;
```

### 5. Pagination
Use LIMIT and OFFSET for pagination:
```javascript
const pageSize = 20;
const page = 1;
const offset = (page - 1) * pageSize;

const products = await db.query(`
  SELECT * FROM products 
  ORDER BY created_at DESC
  LIMIT $1 OFFSET $2
`, [pageSize, offset]);
```

For better performance with large offsets, use keyset pagination:
```sql
SELECT * FROM products 
WHERE created_at < $1  -- Last row's created_at
ORDER BY created_at DESC
LIMIT $2
```

## Data Integrity

### 1. Use Transactions
```javascript
const client = await pool.connect();
try {
  await client.query('BEGIN');
  
  // Create order
  const order = await client.query(
    'INSERT INTO orders (order_number, total) VALUES ($1, $2) RETURNING *',
    [orderNumber, total]
  );
  
  // Insert order items
  for (const item of items) {
    await client.query(
      'INSERT INTO order_items (order_id, product_id, quantity) VALUES ($1, $2, $3)',
      [order.rows[0].id, item.productId, item.quantity]
    );
  }
  
  await client.query('COMMIT');
} catch (e) {
  await client.query('ROLLBACK');
  throw e;
} finally {
  client.release();
}
```

### 2. Use Foreign Key Constraints
All relationships should have constraints:
```sql
ALTER TABLE orders ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
```

### 3. Validate Data Before Insert/Update
```javascript
// Validate email format
if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
  throw new Error('Invalid email format');
}

// Validate price is positive
if (price < 0) {
  throw new Error('Price cannot be negative');
}

// Then insert
await db.query('INSERT INTO products (title, price) VALUES ($1, $2)', [title, price]);
```

## Performance Optimization

### 1. Use EXPLAIN to Analyze Queries
```sql
EXPLAIN ANALYZE 
SELECT p.*, r.rating 
FROM products p
LEFT JOIN product_reviews r ON p.id = r.product_id
WHERE p.category_id = $1
ORDER BY r.rating DESC;
```

### 2. Cache Frequently Accessed Data
```javascript
const redis = require('redis');
const client = redis.createClient();

// Try cache first
let product = await client.get(`product:${id}`);
if (!product) {
  // Fetch from database
  product = await db.query('SELECT * FROM products WHERE id = $1', [id]);
  // Cache for 1 hour
  await client.setEx(`product:${id}`, 3600, JSON.stringify(product));
}
```

### 3. Use Batch Operations
**❌ WRONG (N+1 problem):**
```javascript
for (const productId of productIds) {
  const product = await db.query('SELECT * FROM products WHERE id = $1', [productId]);
  // Process product
}
```

**✅ CORRECT:**
```javascript
const products = await db.query('SELECT * FROM products WHERE id = ANY($1)', [productIds]);
// Process products
```

### 4. Analyze Slow Queries
```sql
-- Enable logging of slow queries
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 1 second
SELECT pg_reload_conf();

-- View logs
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

## Security Best Practices

### 1. Never Log Sensitive Data
```javascript
// ❌ WRONG
console.log(`User login: ${email} - ${password}`);

// ✅ CORRECT
console.log(`User login: ${email}`);
```

### 2. Use Hashing for Passwords
```javascript
const bcrypt = require('bcrypt');

// Hash password
const hashedPassword = await bcrypt.hash(password, 10);

// Verify
const isValid = await bcrypt.compare(password, hashedPassword);
```

### 3. Validate Input Length
```javascript
const MAX_EMAIL_LENGTH = 255;
const MAX_PASSWORD_LENGTH = 255;

if (email.length > MAX_EMAIL_LENGTH) {
  throw new Error('Email too long');
}
```

### 4. Use Row Level Security (RLS) for Multi-tenant Features
```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_orders_policy ON orders
  FOR SELECT
  USING (user_id = current_setting('app.current_user_id')::uuid);
```

## Backup & Recovery

### Regular Backups
```bash
# Daily backup at 2 AM
0 2 * * * pg_dump -U harrison_bull -d harrison_bull_db | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

### Point-in-Time Recovery
Enable WAL archiving:
```
wal_level = replica
archive_mode = on
archive_command = 'cp %p /wal_archive/%f'
```

## Monitoring & Logging

### Monitor Connection Health
```sql
SELECT count(*) as total_connections FROM pg_stat_activity;
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

### Monitor Lock Contention
```sql
SELECT * FROM pg_locks WHERE NOT granted;
```

### Monitor Index Usage
```sql
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Common Pitfalls to Avoid

1. **Selecting too many columns** - Use specific column lists
2. **Missing indexes** - Profile queries and add indexes on hot paths
3. **N+1 queries** - Batch fetch related data
4. **Long transactions** - Keep transactions short
5. **Not using transactions** - Use them for related operations
6. **Hardcoded connection strings** - Use environment variables
7. **Not handling connection errors** - Implement retry logic
8. **Missing timestamps** - Always track created_at and updated_at
9. **Not validating input** - Validate before database operations
10. **Improper error handling** - Catch and log errors appropriately

## Database Maintenance

### Regular Maintenance Tasks
```bash
# Daily
VACUUM ANALYZE;

# Weekly
REINDEX DATABASE harrison_bull_db;

# Monthly
ALTER SYSTEM SET shared_buffers = '4GB';  -- Tune based on server
SELECT pg_reload_conf();
```

### Check Database Health
```sql
-- Table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Missing indexes
SELECT * FROM pg_stat_user_tables WHERE seq_scan > idx_scan;
```

## Testing Database Code

### Test with Transactions
```javascript
describe('Orders API', () => {
  let client;
  
  beforeEach(async () => {
    client = await pool.connect();
    await client.query('BEGIN');
  });
  
  afterEach(async () => {
    await client.query('ROLLBACK');
    client.release();
  });
  
  it('should create order', async () => {
    const result = await client.query(
      'INSERT INTO orders (order_number, total) VALUES ($1, $2) RETURNING *',
      ['ORD-001', 100]
    );
    expect(result.rows[0].order_number).toBe('ORD-001');
  });
});
```

### Use Test Database
```bash
# Create test database
createdb harrison_bull_db_test

# Run tests against test DB
DATABASE_NAME=harrison_bull_db_test npm test
```

## References

- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Connection Pooling Best Practices](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [JSON/JSONB Best Practices](https://www.postgresql.org/docs/current/datatype-json.html)
