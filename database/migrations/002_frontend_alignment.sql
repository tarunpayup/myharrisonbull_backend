-- Harrison Bull E-Commerce Platform
-- Migration 002: Align schema with the frontend (orders, tracking, reviews, blog, stores, banners, CMS)
-- Safe to run on a database created from the earlier schema.sql (idempotent).

-- Users
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_shoe_size VARCHAR(20) DEFAULT 'UK 8.5';
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_width VARCHAR(30) DEFAULT 'D (Regular)';

-- Addresses
ALTER TABLE addresses ADD COLUMN IF NOT EXISTS apartment VARCHAR(255);
ALTER TABLE addresses ALTER COLUMN phone TYPE VARCHAR(30);
ALTER TABLE addresses ALTER COLUMN address_type SET DEFAULT 'Home';

-- Orders (frontend lifecycle: Placed > Confirmed > Packed > Shipped > Out for Delivery > Delivered | Cancelled)
ALTER TABLE orders ALTER COLUMN customer_phone TYPE VARCHAR(30);
ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'Placed';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS courier VARCHAR(100) DEFAULT 'Courier Partner';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS estimated_delivery_date VARCHAR(100);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(50);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address JSONB;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_method JSONB;
UPDATE orders SET status = 'Placed'    WHERE status = 'Pending';
UPDATE orders SET status = 'Packed'    WHERE status = 'Processing';
UPDATE orders SET status = 'Delivered' WHERE status = 'Completed';

CREATE TABLE IF NOT EXISTS order_tracking_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  step_order INT NOT NULL,
  status VARCHAR(50) NOT NULL,
  location VARCHAR(255),
  description TEXT,
  completed BOOLEAN DEFAULT false,
  occurred_at TIMESTAMP,
  UNIQUE(order_id, status)
);
CREATE INDEX IF NOT EXISTS idx_order_tracking_logs_order_id ON order_tracking_logs(order_id);

-- Promotional banners
ALTER TABLE promotional_banners ADD COLUMN IF NOT EXISTS subtitle VARCHAR(500);
ALTER TABLE promotional_banners ADD COLUMN IF NOT EXISTS badge VARCHAR(100);
ALTER TABLE promotional_banners ADD COLUMN IF NOT EXISTS button_text VARCHAR(100);
ALTER TABLE promotional_banners ADD COLUMN IF NOT EXISTS background_color VARCHAR(20);

-- Reviews (moderation + fit feedback)
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Pending';
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS fit_feedback VARCHAR(30) DEFAULT 'True to Size';
UPDATE product_reviews SET status = CASE WHEN is_approved THEN 'Approved' ELSE 'Pending' END WHERE status IS NULL OR status = 'Pending';

-- Blog
ALTER TABLE blog_posts ADD COLUMN IF NOT EXISTS author_name VARCHAR(150);
ALTER TABLE blog_posts ADD COLUMN IF NOT EXISTS author_role VARCHAR(150);
ALTER TABLE blog_posts ADD COLUMN IF NOT EXISTS read_time VARCHAR(50);

-- Stores
ALTER TABLE store_locations ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE store_locations ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);
ALTER TABLE store_locations ADD COLUMN IF NOT EXISTS hours_text VARCHAR(500);
ALTER TABLE store_locations ADD COLUMN IF NOT EXISTS appointment_available BOOLEAN DEFAULT false;
ALTER TABLE store_locations ADD COLUMN IF NOT EXISTS services JSONB DEFAULT '[]'::jsonb;

-- Site content + contact form
CREATE TABLE IF NOT EXISTS site_settings (
  key VARCHAR(100) PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contact_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  subject VARCHAR(255),
  message TEXT NOT NULL,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_contact_messages_created_at ON contact_messages(created_at);
