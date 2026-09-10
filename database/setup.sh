#!/bin/bash

# ============================================================
# DEPRECATED: Use setup-render.sh instead
# ============================================================
# This script is for local PostgreSQL setup only.
# For Render cloud database, use: ./setup-render.sh
# ============================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-harrison_bull_db}"
DB_USER="${DATABASE_USER:-harrison_bull}"
DB_PASSWORD="${DATABASE_PASSWORD:-dev_password_change_in_production}"

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Harrison Bull - Database Setup Script         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check if PostgreSQL is installed
echo -e "${YELLOW}Checking PostgreSQL installation...${NC}"
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL is not installed${NC}"
    echo "Install PostgreSQL from: https://www.postgresql.org/download/"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL found${NC}"
echo ""

# Menu
echo -e "${BLUE}Select setup option:${NC}"
echo "1. Setup with existing PostgreSQL (Local)"
echo "2. Clean database (drops and recreates)"
echo "3. Load seed data only"
echo "4. Reset and reload everything"
echo ""
echo -e "${YELLOW}For Render cloud database, use: ./setup-render.sh${NC}"
echo ""
read -p "Enter option (1-4): " option

case $option in
    1)
        echo ""
        echo -e "${YELLOW}Setting up with existing PostgreSQL...${NC}"
        
        # Prompt for credentials
        read -p "PostgreSQL host [$DB_HOST]: " input
        DB_HOST=${input:-$DB_HOST}
        
        read -p "PostgreSQL port [$DB_PORT]: " input
        DB_PORT=${input:-$DB_PORT}
        
        read -p "PostgreSQL username [postgres]: " input
        ADMIN_USER=${input:-postgres}
        
        read -sp "PostgreSQL password: " ADMIN_PASSWORD
        echo ""
        
        echo -e "${YELLOW}Creating database and user...${NC}"
        
        # Create database and user
        PGPASSWORD=$ADMIN_PASSWORD psql -h $DB_HOST -U $ADMIN_USER -tc \
          "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
        PGPASSWORD=$ADMIN_PASSWORD psql -h $DB_HOST -U $ADMIN_USER -c \
          "CREATE DATABASE $DB_NAME;"
        
        # Create user
        PGPASSWORD=$ADMIN_PASSWORD psql -h $DB_HOST -U $ADMIN_USER -c \
          "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || \
        echo -e "${YELLOW}User already exists${NC}"
        
        # Grant privileges
        PGPASSWORD=$ADMIN_PASSWORD psql -h $DB_HOST -U $ADMIN_USER -c \
          "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
        
        echo -e "${YELLOW}Loading schema...${NC}"
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f schema.sql
        
        echo -e "${GREEN}✓ Schema loaded successfully!${NC}"
        ;;
        
    2)
        echo ""
        echo -e "${RED}⚠️  This will drop and recreate the entire database!${NC}"
        read -p "Are you sure? (yes/no): " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo -e "${YELLOW}Dropping database...${NC}"
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -c \
              "DROP DATABASE IF EXISTS $DB_NAME;"
            
            echo -e "${YELLOW}Creating database...${NC}"
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -c \
              "CREATE DATABASE $DB_NAME;"
            
            echo -e "${YELLOW}Loading schema...${NC}"
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f schema.sql
            
            echo -e "${GREEN}✓ Database cleaned and recreated!${NC}"
        fi
        ;;
        
    3)
        echo ""
        echo -e "${YELLOW}Loading seed data...${NC}"
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f seed_data.sql
        echo -e "${GREEN}✓ Seed data loaded successfully!${NC}"
        ;;
        
    4)
        echo ""
        echo -e "${RED}⚠️  This will drop, recreate, and reload everything!${NC}"
        read -p "Are you sure? (yes/no): " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo -e "${YELLOW}Dropping database...${NC}"
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -c \
              "DROP DATABASE IF EXISTS $DB_NAME;"
            
            echo -e "${YELLOW}Creating database...${NC}"
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -c \
              "CREATE DATABASE $DB_NAME;"
            
            echo -e "${YELLOW}Loading schema...${NC}"
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f schema.sql
            
            echo -e "${YELLOW}Loading seed data...${NC}"
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f seed_data.sql
            
            echo -e "${GREEN}✓ Everything is set up!${NC}"
        fi
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "For Render cloud database setup, use: ./setup-render.sh"
echo ""
