# Harrison Bull E-Commerce Platform - Architecture & Requirements

## Frontend Overview
The Frontend is built with **Next.js 15** (React 19) with TypeScript, TailwindCSS, and uses a client-side store pattern for state management.

---

## Project Structure

### 1. **Root Configuration Files**
- **package.json** - Dependencies and scripts (Next.js, React 19, TailwindCSS, Lucide Icons, Google GenAI)
- **next.config.ts** - Next.js configuration
- **tsconfig.json** - TypeScript configuration
- **eslint.config.mjs** - ESLint configuration
- **.env.example** - Environment variables template
- **postcss.config.mjs** - PostCSS configuration for TailwindCSS
- **metadata.json** - Application metadata

### 2. **App Directory** (`/app`)
Next.js App Router structure with route-based pages and layouts.

#### **Core Layout Files**
- **layout.tsx** - Root layout with metadata, fonts (Cinzel serif, Plus Jakarta Sans), theme setup (dark theme #071324)
- **page.tsx** - Homepage with featured shoes, best sellers, silhouettes, testimonials
- **globals.css** - Global styles

#### **Routes/Pages** (33 page directories)
Each directory contains a `page.tsx` file:

| Route | Purpose | Key Features |
|-------|---------|--------------|
| `/shop` | Product listing page | Browse all shoes, filtering, sorting |
| `/product/[id]` | Product detail page | Single shoe details, images, specifications, reviews, cart actions |
| `/cart` | Shopping cart | View items, quantities, pricing, checkout link |
| `/checkout` | Checkout process | Shipping address, payment, order review |
| `/order-confirmation` | Order success | Order details, tracking info |
| `/orders` | Order history | View past orders, order status |
| `/track` | Order tracking | Track shipment status |
| `/category` | Category browsing | Browse shoes by category (Oxfords, Derbies, etc.) |
| `/search` | Search results | Display search query results |
| `/wishlist` | Saved items | Wishlist/favorites |
| `/profile` | User account | Account details, preferences |
| `/addresses` | Address management | Saved shipping/billing addresses |
| `/register` | User signup | Create new account |
| `/login` | User login | Authentication |
| `/forgot-password` | Password recovery | Reset forgotten password |
| `/admin` | Admin dashboard | Management features (if admin user) |
| `/blog` | Blog listing | Company news/articles |
| `/blog/*` | Blog post detail | Individual blog post |
| `/about` | About us | Company history, craftsmanship info |
| `/craftsmanship` | Craftsmanship guide | Goodyear welted shoe construction process |
| `/contact` | Contact form | Customer inquiry form |
| `/faq` | FAQ page | Frequently asked questions |
| `/returns` | Return policy | Returns and exchanges info |
| `/reviews` | Product reviews | Customer reviews and ratings |
| `/shipping` | Shipping info | Shipping options and costs |
| `/terms` | Terms of service | Legal terms |
| `/privacy` | Privacy policy | Privacy statement |
| `/stores` | Store locations | Physical store locations |
| `/offers` | Promotions | Active offers and coupons |
| `/coupons` | Coupon management | Apply/manage coupons |
| `/notifications` | Notifications | Order/promotion notifications |

---

### 3. **Components** (`/components`)
Reusable React components:

- **Navbar.tsx** - Top navigation bar with logo, search, cart, menu
- **Footer.tsx** - Footer with links, contact, social
- **CartDrawer.tsx** - Shopping cart sidebar drawer
- **ClientLayoutWrapper.tsx** - Client-side layout wrapper (handles hydration)
- **ShoeCard.tsx** - Product card component (image, title, price, rating)
- **SearchModal.tsx** - Search/modal component for product search
- **GoodyearWeltDiagram.tsx** - Educational diagram showing shoe construction
- **HarrisonBullLogo.tsx** - Logo component

---

### 4. **Hooks** (`/hooks`)
Custom React hooks:

- **use-mobile.ts** - Detect mobile/responsive breakpoints

---

### 5. **Types** (`/types`)
TypeScript type definitions:

- **shoe.ts** - Core data models (see detailed schema below)

---

### 6. **Library** (`/lib`)

#### **store.tsx** (State Management)
Context-based store managing:
- Shoes inventory
- Shopping cart items
- Orders history
- User profile
- Addresses
- Coupons and promotions
- Reviews
- Blog posts
- Store locations
- Notifications

#### **data/initialData.ts** (Mock Data)
Initial data for development:
- INITIAL_SHOES - Sample shoe products
- INITIAL_BANNERS - Promotional banners
- INITIAL_COUPONS - Coupon codes
- INITIAL_REVIEWS - Product reviews
- INITIAL_BLOG_POSTS - Blog content
- INITIAL_STORES - Store locations
- INITIAL_ORDERS - Sample orders
- INITIAL_USER - Default user profile

#### **utils.ts** - Utility functions

---

### 7. **Public** (`/public`)
Static assets (images, fonts, icons)

---

## Data Models (TypeScript Interfaces)

### **ShoeProduct**
```typescript
{
  id: string;
  title: string;
  slug: string;
  sku: string;
  category: 'Oxfords' | 'Derbies' | 'Monk Straps' | 'Chelsea Boots' | 'Chukka Boots' | 'Loafers' | 'Brogues';
  price: number;
  originalPrice?: number;
  discountPercent?: number;
  shortDescription: string;
  description: string;
  specifications: {
    weltType: string;
    leather: string;
    sole: string;
    last: string;
    lining: string;
    craftingTime: string;
    resolable: boolean;
    origin: string;
  };
  images: string[];
  sizes: { [size: string]: number }; // e.g. {"UK 7": 5}
  color: string;
  colorHex: string;
  rating: number;
  reviewsCount: number;
  isBestSeller?: boolean;
  isFeatured?: boolean;
  isNew?: boolean;
  inStock: boolean;
  createdAt: string;
}
```

### **CartItem**
```typescript
{
  shoeId: string;
  size: string;
  quantity: number;
  price: number;
}
```

### **Order**
```typescript
{
  id: string;
  orderNumber: string;
  customerId?: string;
  customerName: string;
  customerEmail: string;
  customerPhone: string;
  items: CartItem[];
  subtotal: number;
  tax: number;
  shippingCost: number;
  discount?: number;
  total: number;
  status: 'Pending' | 'Processing' | 'Shipped' | 'Delivered' | 'Cancelled' | 'Returned';
  shippingAddress: CustomerAddress;
  paymentMethod?: string;
  paymentStatus?: 'Paid' | 'Pending' | 'Refunded';
  trackingNumber?: string;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}
```

### **UserProfile**
```typescript
{
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  phone?: string;
  addresses: CustomerAddress[];
  orders: Order[];
  wishlist: string[]; // shoe IDs
  preferences: {
    newsletter?: boolean;
    promotions?: boolean;
  };
  createdAt: string;
  updatedAt: string;
}
```

### **CustomerAddress**
```typescript
{
  id: string;
  firstName: string;
  lastName: string;
  company?: string;
  street: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
  phone: string;
  isDefault?: boolean;
}
```

### **ProductReview**
```typescript
{
  id: string;
  shoeId: string;
  customerId: string;
  rating: number; // 1-5
  title: string;
  comment: string;
  createdAt: string;
}
```

### **Coupon**
```typescript
{
  id: string;
  code: string;
  description: string;
  discountType: 'percentage' | 'fixed';
  discountValue: number;
  minOrderAmount?: number;
  maxUses?: number;
  usedCount: number;
  expiresAt?: string;
  isActive: boolean;
}
```

### **PromotionalBanner**
```typescript
{
  id: string;
  title: string;
  description: string;
  image: string;
  link?: string;
  order: number; // for carousel ordering
}
```

### **BlogPost**
```typescript
{
  id: string;
  slug: string;
  title: string;
  content: string;
  excerpt: string;
  author: string;
  image: string;
  category: string;
  published: boolean;
  createdAt: string;
  updatedAt: string;
}
```

### **StoreLocation**
```typescript
{
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
  phone: string;
  email?: string;
  hours: {
    [day: string]: { open: string; close: string }; // "Mon-Fri": {"open": "10:00", "close": "18:00"}
  };
  latitude?: number;
  longitude?: number;
}
```

---

## Required Backend APIs

The backend must provide RESTful API endpoints to support the frontend functionality:

### **Authentication**
- POST `/api/auth/register` - Create new user account
- POST `/api/auth/login` - User login
- POST `/api/auth/logout` - User logout
- POST `/api/auth/forgot-password` - Reset password request
- POST `/api/auth/reset-password` - Confirm password reset
- GET `/api/auth/me` - Get current user profile

### **Products**
- GET `/api/products` - List all products with pagination, filtering, sorting
- GET `/api/products/:id` - Get single product details
- GET `/api/products/by-slug/:slug` - Get product by slug
- GET `/api/products/search?q=query` - Search products
- GET `/api/categories` - List product categories
- GET `/api/products/:id/reviews` - Get product reviews

### **Cart** (Client-side managed via store, but backend needed for checkout)
- POST `/api/cart/validate` - Validate cart items before checkout
- GET `/api/cart/shipping-options` - Get available shipping methods

### **Orders**
- POST `/api/orders` - Create new order
- GET `/api/orders` - Get user's order history
- GET `/api/orders/:id` - Get order details
- GET `/api/orders/:id/track` - Get order tracking info
- PUT `/api/orders/:id` - Update order (cancel, etc.)

### **Users**
- GET `/api/users/profile` - Get user profile
- PUT `/api/users/profile` - Update user profile
- GET `/api/users/addresses` - Get user addresses
- POST `/api/users/addresses` - Create new address
- PUT `/api/users/addresses/:id` - Update address
- DELETE `/api/users/addresses/:id` - Delete address
- GET `/api/users/wishlist` - Get wishlist items
- POST `/api/users/wishlist` - Add to wishlist
- DELETE `/api/users/wishlist/:shoeId` - Remove from wishlist

### **Reviews**
- POST `/api/reviews` - Create product review
- PUT `/api/reviews/:id` - Update review
- DELETE `/api/reviews/:id` - Delete review

### **Coupons & Promotions**
- GET `/api/coupons` - List active coupons
- POST `/api/coupons/validate` - Validate coupon code
- GET `/api/banners` - Get promotional banners

### **Blog**
- GET `/api/blog` - List blog posts
- GET `/api/blog/:slug` - Get single blog post

### **Store Locations**
- GET `/api/stores` - Get all store locations

---

## Key Features Required

### **E-Commerce Features**
✅ Product catalog with multiple images, specifications, sizing  
✅ Shopping cart functionality  
✅ User authentication (register, login, password reset)  
✅ Order management (creation, tracking, status)  
✅ Address book management  
✅ Wishlist functionality  
✅ Product reviews and ratings  
✅ Coupon/discount system  
✅ Shipping options with costs  
✅ Order status tracking  

### **Content Management**
✅ Blog system for articles/news  
✅ Promotional banners  
✅ FAQ/Help pages  
✅ Policy pages (Terms, Privacy, Returns, Shipping)  
✅ Store locations directory  

### **Admin Features**
✅ Product management (CRUD)  
✅ Order management  
✅ User management  
✅ Coupon management  
✅ Blog post management  
✅ Banner management  

---

## Technology Stack Recommendations for Backend

- **Framework**: Node.js (Express, Fastify) or Python (Django, Flask)
- **Database**: PostgreSQL or MongoDB
- **Authentication**: JWT tokens
- **File Storage**: AWS S3 or similar for product images
- **API Documentation**: Swagger/OpenAPI
- **Payment Integration**: Stripe or similar (if needed for checkout)
- **Email**: Transactional email service (SendGrid, Mailgun)

---

## Development Priorities

1. **Phase 1 (Core)**: Authentication, Products API, Orders API
2. **Phase 2 (Users)**: User profiles, Addresses, Wishlist
3. **Phase 3 (Shop Features)**: Reviews, Coupons, Shipping
4. **Phase 4 (Content)**: Blog, Store locations, Admin panel
5. **Phase 5 (Advanced)**: Payment processing, Analytics, Notifications

---

## Notes

- Frontend uses client-side store (no Redux/separate state library) - Backend should be REST API
- All product images currently use Unsplash URLs (placeholder) - Backend should serve images
- Mock data in `initialData.ts` shows expected data structure
- Theme uses dark mode (#071324 background, gold accents #c89255)
- Responsive design with mobile-first approach
- No backend URL configured yet - will need environment variable configuration
