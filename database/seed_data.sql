-- Harrison Bull E-Commerce Platform
-- Sample Seed Data for Development
-- Created: 2026-09-10

-- ============================================================
-- SEED USERS
-- ============================================================

-- Admin User (Password: admin123)
INSERT INTO users (email, password_hash, first_name, last_name, is_admin, newsletter_subscribed)
VALUES (
  'admin@harrisonbull.com',
  '$2b$10$YOvVHdm8S8nQlEFLW.8q3e5x8H6Z2K7J9L5N0P8Q1R2S3T4U5V6W7X',
  'Admin',
  'User',
  true,
  true
);

-- Test User 1
INSERT INTO users (email, password_hash, first_name, last_name, newsletter_subscribed)
VALUES (
  'john@example.com',
  '$2b$10$YOvVHdm8S8nQlEFLW.8q3e5x8H6Z2K7J9L5N0P8Q1R2S3T4U5V6W7X',
  'John',
  'Doe',
  true
);

-- Test User 2
INSERT INTO users (email, password_hash, first_name, last_name, phone)
VALUES (
  'jane@example.com',
  '$2b$10$YOvVHdm8S8nQlEFLW.8q3e5x8H6Z2K7J9L5N0P8Q1R2S3T4U5V6W7X',
  'Jane',
  'Smith',
  '+1-555-0123'
);


-- ============================================================
-- SEED CATEGORIES
-- ============================================================

INSERT INTO categories (name, slug, description, display_order)
VALUES
  ('Oxfords', 'oxfords', 'Classic formal cap-toe and wholecut oxfords with hand-welted construction', 1),
  ('Derbies', 'derbies', 'Open-laced dress shoes with versatile styling', 2),
  ('Monk Straps', 'monk-straps', 'Distinctive buckle-closure shoes for refined style', 3),
  ('Chelsea Boots', 'chelsea-boots', 'Elastic-sided boots combining elegance and comfort', 4),
  ('Chukka Boots', 'chukka-boots', 'Desert-inspired ankle boots in premium leather', 5),
  ('Loafers', 'loafers', 'Slip-on shoes for casual and business-casual wear', 6),
  ('Brogues', 'brogues', 'Detailed perforated shoes with decorative wing tips', 7);


-- ============================================================
-- SEED PRODUCTS
-- ============================================================

INSERT INTO products (title, slug, sku, category_id, price, original_price, discount_percent, short_description, description, color, color_hex, rating, reviews_count, is_best_seller, is_featured, is_new, in_stock, total_stock_quantity)
SELECT 
  'The Mayfair Cap-Toe Oxford',
  'mayfair-cap-toe-oxford',
  'HB-OXF-001-BLK',
  id,
  460.00,
  520.00,
  11,
  'Quintessential British formal cap-toe oxford with closed-channel Goodyear welted oak bark sole.',
  'The definitive dress shoe for the discerning gentleman. Hand-lasted in our workshop from Grade-A French Tanneries du Puy box calf. The Mayfair features a tight fiddleback waist, closed-channel single oak-bark sole, and 360° Goodyear hand welt construction that molds effortlessly to your feet and can be resoled indefinitely.',
  'Deep Midnight Black',
  '#0f172a',
  4.9,
  38,
  true,
  true,
  false,
  true,
  58
FROM categories WHERE slug = 'oxfords' LIMIT 1;

INSERT INTO products (title, slug, sku, category_id, price, original_price, discount_percent, short_description, description, color, color_hex, rating, reviews_count, is_best_seller, is_featured, is_new, in_stock, total_stock_quantity)
SELECT 
  'The St. James Wholecut Oxford',
  'st-james-wholecut-oxford',
  'HB-OXF-002-BUR',
  id,
  540.00,
  595.00,
  9,
  'Flawless seamless wholecut cut from a single piece of Annonay museum calf with hand-burnished patina.',
  'The pinnacle of shoemaking difficulty. An unbroken hide of French Annonay museum calf requires pristine leather selection with zero flaws. Hand-blocked and stretched over 2 weeks on the last to achieve a sculpted, glove-like silhouette. Hand-beveled waist and concealed channel welt.',
  'Burgundy Museum Patina',
  '#4a1525',
  5.0,
  29,
  true,
  true,
  true,
  true,
  33
FROM categories WHERE slug = 'oxfords' LIMIT 1;

INSERT INTO products (title, slug, sku, category_id, price, short_description, description, color, color_hex, rating, reviews_count, is_best_seller, is_featured, in_stock, total_stock_quantity)
SELECT 
  'The Chelsea Heritage Boot',
  'chelsea-heritage-boot',
  'HB-CHE-001-BLK',
  id,
  520.00,
  'Elastic-sided Chelsea boot with Goodyear welted oak bark sole.',
  'A sophisticated take on the timeless Chelsea silhouette. Crafted from premium French box calf with elasticated side gussets for effortless entry. The heritage design features our signature hand-welted construction with a double oak bark leather sole.',
  'Black',
  '#000000',
  4.8,
  22,
  true,
  false,
  true,
  42
FROM categories WHERE slug = 'chelsea-boots' LIMIT 1;

INSERT INTO products (title, slug, sku, category_id, price, short_description, description, color, color_hex, rating, reviews_count, is_featured, in_stock, total_stock_quantity)
SELECT 
  'The Classic Penny Loafer',
  'classic-penny-loafer',
  'HB-LOA-001-BRN',
  id,
  380.00,
  'Timeless penny loafer in premium leather with hand-stitched vamp.',
  'A wardrobe essential combining comfort and versatility. Hand-stitched in our workshop using vegetable-tanned leather, this penny loafer features our supportive oak bark sole and can be resoled indefinitely.',
  'Rich Brown',
  '#6b4423',
  4.7,
  18,
  true,
  true,
  25
FROM categories WHERE slug = 'loafers' LIMIT 1;


-- ============================================================
-- SEED PRODUCT SPECIFICATIONS
-- ============================================================

INSERT INTO product_specifications (product_id, welt_type, leather_type, sole_type, last_name, lining_material, crafting_time_hours, crafting_operations, is_resolable, origin_location)
SELECT id, '360° Goodyear Hand Welted with rapid stitch', 'French Box Calf (Tanneries du Puy)', 'Single Oak Bark Tanned Leather (JR Rendenbach)', 'Harrison Chiseled 88 (Medium Almond Toe)', 'Full grain vegetable-tanned calfskin', 48, 212, true, 'Northamptonshire Workshop'
FROM products WHERE slug = 'mayfair-cap-toe-oxford' LIMIT 1;

INSERT INTO product_specifications (product_id, welt_type, leather_type, sole_type, last_name, lining_material, crafting_time_hours, crafting_operations, is_resolable, origin_location)
SELECT id, '270° Goodyear Hand Welt with beveled waist', 'French Museum Calf (Tannerie d''Annonay)', 'Hand-Fiddleback Oak Bark Leather Sole with brass nail heel', 'Harrison Sleek 72 Last (Classic Soft Square)', 'Natural veg-tan glove leather', 54, 230, true, 'Harrison Bull Atelier'
FROM products WHERE slug = 'st-james-wholecut-oxford' LIMIT 1;

INSERT INTO product_specifications (product_id, welt_type, leather_type, sole_type, last_name, lining_material, crafting_time_hours, crafting_operations, is_resolable, origin_location)
SELECT id, '360° Goodyear Hand Welted', 'French Box Calf', 'Oak Bark Tanned Single Sole', 'Harrison Classic 95 Last', 'Vegetable-tanned calfskin', 45, 200, true, 'Northamptonshire Workshop'
FROM products WHERE slug = 'chelsea-heritage-boot' LIMIT 1;

INSERT INTO product_specifications (product_id, welt_type, leather_type, sole_type, last_name, lining_material, crafting_time_hours, crafting_operations, is_resolable, origin_location)
SELECT id, '360° Hand-Stitched Welt', 'Vegetable-Tanned Calf', 'Oak Bark Tanned Single Sole', 'Harrison Comfort 80 Last', 'Full grain leather lining', 38, 185, true, 'Northamptonshire Workshop'
FROM products WHERE slug = 'classic-penny-loafer' LIMIT 1;


-- ============================================================
-- SEED PRODUCT SIZES
-- ============================================================

-- Mayfair Cap-Toe Oxford Sizes
INSERT INTO product_sizes (product_id, size, stock_quantity)
SELECT id, size, qty FROM (
  SELECT (SELECT id FROM products WHERE slug = 'mayfair-cap-toe-oxford' LIMIT 1) as id, size, qty FROM (
    VALUES 
      ('UK 6.0', 3), ('UK 6.5', 4), ('UK 7.0', 6), ('UK 7.5', 8), ('UK 8.0', 12),
      ('UK 8.5', 9), ('UK 9.0', 7), ('UK 9.5', 5), ('UK 10.0', 4), ('UK 10.5', 2), ('UK 11.0', 3)
  ) AS t(size, qty)
);

-- St. James Wholecut Oxford Sizes
INSERT INTO product_sizes (product_id, size, stock_quantity)
SELECT id, size, qty FROM (
  SELECT (SELECT id FROM products WHERE slug = 'st-james-wholecut-oxford' LIMIT 1) as id, size, qty FROM (
    VALUES 
      ('UK 6.5', 2), ('UK 7.0', 5), ('UK 7.5', 7), ('UK 8.0', 8), ('UK 8.5', 6),
      ('UK 9.0', 5), ('UK 9.5', 3), ('UK 10.0', 2), ('UK 10.5', 1), ('UK 11.0', 2)
  ) AS t(size, qty)
);

-- Chelsea Heritage Boot Sizes
INSERT INTO product_sizes (product_id, size, stock_quantity)
SELECT id, size, qty FROM (
  SELECT (SELECT id FROM products WHERE slug = 'chelsea-heritage-boot' LIMIT 1) as id, size, qty FROM (
    VALUES 
      ('UK 6.5', 3), ('UK 7.0', 4), ('UK 7.5', 6), ('UK 8.0', 9), ('UK 8.5', 8),
      ('UK 9.0', 6), ('UK 9.5', 4), ('UK 10.0', 3), ('UK 10.5', 2), ('UK 11.0', 3)
  ) AS t(size, qty)
);

-- Classic Penny Loafer Sizes
INSERT INTO product_sizes (product_id, size, stock_quantity)
SELECT id, size, qty FROM (
  SELECT (SELECT id FROM products WHERE slug = 'classic-penny-loafer' LIMIT 1) as id, size, qty FROM (
    VALUES 
      ('UK 6.0', 2), ('UK 6.5', 3), ('UK 7.0', 5), ('UK 7.5', 6), ('UK 8.0', 8),
      ('UK 8.5', 6), ('UK 9.0', 4), ('UK 9.5', 3), ('UK 10.0', 2), ('UK 10.5', 1)
  ) AS t(size, qty)
);


-- ============================================================
-- SEED PRODUCT IMAGES
-- ============================================================

-- Mayfair Oxford Images
INSERT INTO product_images (product_id, image_url, alt_text, display_order, is_primary)
SELECT id, url, alt, ord, isprim FROM (
  SELECT (SELECT id FROM products WHERE slug = 'mayfair-cap-toe-oxford' LIMIT 1) as id, url, alt, ord, isprim FROM (
    VALUES 
      ('https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?q=80&w=1200&auto=format&fit=crop', 'Mayfair Oxford Front View', 1, true),
      ('https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?q=80&w=1200&auto=format&fit=crop', 'Mayfair Oxford Side View', 2, false),
      ('https://images.unsplash.com/photo-1533867617858-e7b97e060509?q=80&w=1200&auto=format&fit=crop', 'Mayfair Oxford Detail', 3, false),
      ('https://images.unsplash.com/photo-1560343090-f0409e92791a?q=80&w=1200&auto=format&fit=crop', 'Mayfair Oxford Sole', 4, false)
  ) AS t(url, alt, ord, isprim)
);

-- St. James Oxford Images
INSERT INTO product_images (product_id, image_url, alt_text, display_order, is_primary)
SELECT id, url, alt, ord, isprim FROM (
  SELECT (SELECT id FROM products WHERE slug = 'st-james-wholecut-oxford' LIMIT 1) as id, url, alt, ord, isprim FROM (
    VALUES 
      ('https://images.unsplash.com/photo-1549298916-b41d501d3772?q=80&w=1200&auto=format&fit=crop', 'St. James Wholecut Front', 1, true),
      ('https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?q=80&w=1200&auto=format&fit=crop', 'St. James Wholecut Side', 2, false),
      ('https://images.unsplash.com/photo-1533867617858-e7b97e060509?q=80&w=1200&auto=format&fit=crop', 'St. James Wholecut Detail', 3, false)
  ) AS t(url, alt, ord, isprim)
);


-- ============================================================
-- SEED PROMOTIONAL BANNERS
-- ============================================================

INSERT INTO promotional_banners (title, description, image_url, link_url, display_order, is_active)
VALUES
  ('Summer Collection', 'Explore our latest summer collection of hand-crafted shoes', 'https://images.unsplash.com/photo-1542272604-787c62d465d1?q=80&w=1200&auto=format&fit=crop', '/shop', 1, true),
  ('Craftsmanship Guide', 'Learn about our Goodyear welting process', 'https://images.unsplash.com/photo-1491553895911-0055eca6402d?q=80&w=1200&auto=format&fit=crop', '/craftsmanship', 2, true),
  ('New Arrivals', 'Check out what''s new this season', 'https://images.unsplash.com/photo-1460353581641-37baddab0fa2?q=80&w=1200&auto=format&fit=crop', '/shop', 3, true);


-- ============================================================
-- SEED COUPONS
-- ============================================================

INSERT INTO coupons (code, description, discount_type, discount_value, min_order_amount, max_uses, expires_at, is_active)
VALUES
  ('WELCOME10', '10% off for new customers', 'percentage', 10, 0, 100, '2026-12-31', true),
  ('SUMMER20', '20% off entire summer collection', 'percentage', 20, 100, 50, '2026-09-30', true),
  ('FLAT50', 'Flat $50 off orders over $500', 'fixed', 50, 500, 30, '2026-10-15', true);


-- ============================================================
-- SEED PRODUCT REVIEWS
-- ============================================================

INSERT INTO product_reviews (product_id, user_id, customer_name, email, rating, title, comment, verified_purchase, is_approved)
SELECT p.id, u.id, u.first_name || ' ' || u.last_name, u.email, rating, title, comment, true, true
FROM (
  SELECT 'mayfair-cap-toe-oxford'::text as slug, 5 as rating, 'Exceptional Craftsmanship' as title, 'These shoes are absolutely stunning. The leather feels buttery soft and the construction is impeccable. Worth every penny!' as comment
  UNION ALL
  SELECT 'mayfair-cap-toe-oxford', 5, 'Best Investment Shoes', 'I have worn these daily for 6 months. They have molded perfectly to my feet. The sole is still in pristine condition. Highly recommend!'
  UNION ALL
  SELECT 'st-james-wholecut-oxford', 5, 'Shoemaking Excellence', 'The attention to detail is remarkable. These are museum-quality shoes that will last a lifetime.'
) reviews
JOIN products p ON p.slug = reviews.slug
JOIN users u ON u.email IN ('john@example.com', 'jane@example.com')
LIMIT 4;


-- ============================================================
-- SEED STORE LOCATIONS
-- ============================================================

INSERT INTO store_locations (name, street_address, city, state, postal_code, country, phone, email, latitude, longitude)
VALUES
  ('Harrison Bull - London Flagship', '123 Savile Row', 'London', 'England', 'W1S 3PR', 'United Kingdom', '+44-20-7734-5010', 'london@harrisonbull.com', 51.5148, -0.1397),
  ('Harrison Bull - New York', '456 Madison Avenue', 'New York', 'NY', '10022', 'United States', '+1-212-555-0147', 'newyork@harrisonbull.com', 40.7614, -73.9776),
  ('Harrison Bull - Tokyo', '789 Ginza', 'Tokyo', 'Tokyo', '104-0061', 'Japan', '+81-3-6218-3341', 'tokyo@harrisonbull.com', 35.6705, 139.7636),
  ('Harrison Bull - Sydney', '321 Pitt Street', 'Sydney', 'NSW', '2000', 'Australia', '+61-2-9231-4921', 'sydney@harrisonbull.com', -33.8688, 151.2093);


-- ============================================================
-- SEED STORE HOURS
-- ============================================================

-- London Store Hours
INSERT INTO store_hours (store_id, day_of_week, opening_time, closing_time, is_closed)
SELECT id, day, opening, closing, false FROM (
  SELECT (SELECT id FROM store_locations WHERE name = 'Harrison Bull - London Flagship' LIMIT 1) as id,
    day, opening, closing FROM (
    VALUES 
      (1, '10:00'::time, '18:00'::time), -- Monday
      (2, '10:00'::time, '18:00'::time), -- Tuesday
      (3, '10:00'::time, '18:00'::time), -- Wednesday
      (4, '10:00'::time, '18:00'::time), -- Thursday
      (5, '10:00'::time, '19:00'::time), -- Friday
      (6, '10:00'::time, '17:00'::time), -- Saturday
      (0, NULL, NULL)                     -- Sunday (closed)
  ) AS t(day, opening, closing)
);

-- New York Store Hours
INSERT INTO store_hours (store_id, day_of_week, opening_time, closing_time, is_closed)
SELECT id, day, opening, closing, false FROM (
  SELECT (SELECT id FROM store_locations WHERE name = 'Harrison Bull - New York' LIMIT 1) as id,
    day, opening, closing FROM (
    VALUES 
      (1, '10:00'::time, '18:00'::time),
      (2, '10:00'::time, '18:00'::time),
      (3, '10:00'::time, '18:00'::time),
      (4, '10:00'::time, '18:00'::time),
      (5, '10:00'::time, '19:00'::time),
      (6, '11:00'::time, '17:00'::time),
      (0, NULL, NULL)
  ) AS t(day, opening, closing)
);


-- ============================================================
-- SEED BLOG POSTS
-- ============================================================

INSERT INTO blog_posts (slug, title, content, excerpt, author_id, category, is_published, published_at)
SELECT 
  'the-art-of-goodyear-welting',
  'The Art of Goodyear Welting',
  'Goodyear welting is a time-honored shoemaking technique that has been perfected over more than a century. Unlike cemented construction, a Goodyear-welted shoe features a welt—a strip of leather sewn to the shoe''s insole and the upper. This allows the shoe to be completely disassembled and resoled indefinitely...',
  'Discover the centuries-old shoemaking technique behind our finest creations.',
  id,
  'Craftsmanship',
  true,
  '2026-08-15'::timestamp
FROM users WHERE email = 'admin@harrisonbull.com' LIMIT 1;

INSERT INTO blog_posts (slug, title, content, excerpt, author_id, category, is_published, published_at)
SELECT 
  'why-french-leather-matters',
  'Why French Leather Matters',
  'French leather tanneries have been producing some of the world''s finest leather for centuries. We source exclusively from premium tanneries like Tanneries du Puy and Tannerie d''Annonay. These artisanal tanneries use traditional methods including vegetable tanning...',
  'Explore the heritage and quality of French leather in Harrison Bull shoes.',
  id,
  'Materials',
  true,
  '2026-08-10'::timestamp
FROM users WHERE email = 'admin@harrisonbull.com' LIMIT 1;
