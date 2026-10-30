# Harrison Bull API

Base URL: `http://localhost:5000/api` (set `NEXT_PUBLIC_API_URL` in the frontend). Health checks live at `/health` and `/api/health`.

- All bodies are JSON with **snake_case** keys. Every field maps to the frontend types in `types/shoe.ts` (`original_price` → `originalPrice`, …).
- Authenticated routes need `Authorization: Bearer <access_token>` (from `/auth/login` or `/auth/register`, valid 7 days).
- Errors always look like `{ "error": "message" }` with 400 (validation), 401 (no/invalid token), 403 (not admin / suspended), 404, 409 (conflict, e.g. out of stock), 500.
- Lists are paginated with `?page=&limit=` and return `pagination: { page, limit, total, pages }`.

## Database

`database/schema.sql` is the source of truth (`seed_data.sql` loads sample data; all seed users share the dev password `admin123`, admin is `admin@harrisonbull.com`). An existing database created from the earlier schema is upgraded with `database/migrations/002_frontend_alignment.sql` (idempotent).

## Auth — `/auth`

| Method | Path | Notes |
|---|---|---|
| POST | `/register` | `{email, password(min 6), first_name, last_name}` or `{email, password, name}`; optional `phone`, `preferred_shoe_size`. → 201 `{user, access_token}` |
| POST | `/login` | `{email, password}` → `{user, access_token}`. Suspended accounts get 403 |
| GET | `/me` | 🔒 current user |
| POST | `/logout` | stateless; client discards the token |
| POST | `/change-password` | 🔒 `{current_password, new_password}` |
| POST | `/forgot-password` | `{email}`. Same answer whether or not the account exists. The reset link is logged (no email provider is wired up yet); with `DEBUG=true` the response also carries `reset_token` |
| POST | `/reset-password` | `{token, password}`. Tokens last 1 hour and are single-use |

`user`: `id, name, first_name, last_name, email, phone, role, is_admin, status, preferred_shoe_size, preferred_width, newsletter_subscribed, promotions_enabled, created_at`.

## Products — `/products` (public)

- `GET /` filters: `category_id`, `category` (name or slug), `search`, `featured`, `best_seller`, `new`, `in_stock`, `min_price`, `max_price`; `sort_by` = `price_asc | price_desc | rating | newest`.
- `GET /categories`, `GET /search?q=`, `GET /by-slug/<slug>`, `GET /<id-or-slug>`.

Product: `id, title, slug, sku, category_id, category, category_slug, price, original_price, discount_percent, short_description, description, color, color_hex, rating, reviews_count, is_best_seller, is_featured, is_new, in_stock, images[] (URLs, primary first), sizes{ "UK 8": stock }, specifications{welt_type, leather_type, sole_type, last, lining, crafting_time, crafting_time_hours, resolable, origin}, created_at`.

## Orders — `/orders`

`POST /` (guests allowed; send the token to attach the order to the account):

```json
{
  "items": [{ "product_id": "…", "size": "UK 8", "quantity": 1 }],
  "shipping_address_id": "…",            // or "shipping_address": {full_name, phone, street, apartment, city, state, postal_code, country}
  "customer_email": "…",                 // required for guests; name/phone default from the address
  "coupon_code": "WELT10",
  "payment_method": "Card",
  "delivery_method": { "id": "del-express", "name": "Courier Partner", "estimated_days": "3-5 Business Days" },
  "special_instructions": "Leave at door"
}
```

Prices, discount, shipping (free over $300, otherwise $25) and stock are **calculated and reserved on the server**; client-sent prices are ignored. `payment_status` starts as `Pending` — no gateway is attached, an admin marks it `Paid`.

| Method | Path | Notes |
|---|---|---|
| GET | `/` | 🔒 my orders |
| GET | `/<id or order number>` | 🔒 owner or admin |
| GET | `/<id or order number>/track` | public, no personal details; includes `tracking_logs` |
| POST | `/<id or order number>/cancel` | 🔒 owner, only while `Placed/Confirmed/Packed`; stock is returned |

Order status lifecycle: `Placed → Confirmed → Packed → Shipped → Out for Delivery → Delivered`, or `Cancelled`. Order fields: `id, order_number, customer_id, customer_name/email/phone, items[{shoe_id, title, image, price, size, color, quantity, sku}], shipping_address, delivery_method, payment_method, payment_status, subtotal, discount, coupon_code, shipping_fee, total, status, created_at, estimated_delivery_date, tracking_number, courier, tracking_logs[{status, timestamp, location, description, completed}], special_instructions`.

## Users — `/users` 🔒

- `GET|PUT /profile` — PUT accepts `name` or `first_name/last_name`, `phone`, `preferred_shoe_size`, `preferred_width`, `newsletter_subscribed`, `promotions_enabled`, `avatar_url`. GET also returns `addresses`, `orders_count`, `total_spent`.
- `GET|POST /addresses`, `PUT|DELETE /addresses/<id>` — accepts `full_name`, `phone`, `street`, `apartment`, `city`, `state`, `postal_code`, `country`, `address_type` (`Home|Office`), `is_default`. The first address becomes the default; making another default clears the rest.
- `GET /wishlist` (full product objects + `product_ids`), `POST /wishlist {product_id}` (idempotent), `DELETE /wishlist/<product_id>`.

## Reviews — `/reviews`

- `GET /?product_id=` approved reviews only. `POST /` 🔒 `{product_id, rating 1-5, title, comment(≥10), fit_feedback}` → saved as `Pending` until approved. `DELETE /<id>` 🔒 own review. `POST /<id>/helpful` 🔒.
- Product `rating`/`reviews_count` are computed from approved reviews only.

## Coupons — `/coupons`

- `GET /` currently usable coupons. `POST /validate {code, cart_total}` → `{valid, discount_amount, …}` or 400 with a message.
- Usage is counted when an order is placed. The old public `/apply` and `/redeem` endpoints were removed (anyone could burn a coupon's limit).

## Content (public)

- `GET /blog` (`category`, `search`), `/blog/categories`, `/blog/by-slug/<slug>`, `/blog/related/<id>`, `/blog/<id-or-slug>`.
- `GET /stores`, `/stores/search?q=`, `/stores/nearest?latitude=&longitude=&limit=`, `/stores/<id>`.
- `GET /banners` active banners inside their date window.
- `GET /site-content` → `{content}` (the admin-edited navbar/footer/page content, or `null` to use frontend defaults).
- `POST /contact {name, email, subject?, message}`.
- `/notifications` 🔒: `GET /`, `POST /<id>/read`, `POST /read-all`, `DELETE /`. Customers get order/payment updates; admins get a notification for every new or cancelled order.

## Admin — `/admin` 🔒 (admin users only)

| Area | Endpoints |
|---|---|
| Dashboard | `GET /dashboard`, `GET /analytics/sales?period=daily\|weekly\|monthly` |
| Products | `GET /products`, `GET /products/<id>`, `POST /products`, `PUT /products/<id>`, `DELETE /products/<id>` (soft delete). Body: product fields + `category` or `category_id`, `images: [url]`, `sizes: {"UK 8": 5}`, `specifications: {…}`. `images`/`sizes` replace the existing set only when sent; stock and `in_stock` follow `sizes` |
| Orders | `GET /orders?status=&q=`, `GET /orders/<id>`, `PUT /orders/<id>/status {status, location?, note?}` (updates the timeline, notifies the customer, restocks on cancel), `PUT /orders/<id>/payment {payment_status}` |
| Users | `GET /users?q=`, `PUT /users/<id>/status {is_active}` |
| Coupons | `GET|POST /coupons`, `PUT|DELETE /coupons/<id>` — accepts `discount_percent` **or** `discount_amount`, `min_spend`, `max_uses`, `expires_at`, `active` |
| Banners | `GET|POST /banners`, `PUT|DELETE /banners/<id>` |
| Reviews | `GET /reviews?status=`, `PUT /reviews/<id>/status {status: Approved\|Pending\|Rejected}`, `DELETE /reviews/<id>` |
| Blog | `GET|POST /blog`, `PUT|DELETE /blog/<id>` |
| Stores | `GET|POST /stores`, `PUT|DELETE /stores/<id>` (`coordinates: {lat, lng}`, `services: []`, `hours`) |
| Site content | `PUT /site-content {content}`, `DELETE /site-content` |
| Messages | `GET /messages`, `POST /messages/<id>/read` |
