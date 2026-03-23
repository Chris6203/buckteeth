#!/usr/bin/env bash
set -euo pipefail

# === Buckteeth Server Setup for Ubuntu 22.04/24.04 ===
# Run as root: bash deploy/setup.sh

APP_DIR="/opt/buckteeth"
APP_USER="buckteeth"

echo "==> Installing system packages..."
apt-get update
apt-get install -y \
    python3.12 python3.12-venv python3.12-dev \
    postgresql postgresql-contrib \
    nginx \
    nodejs npm \
    gcc libpq-dev \
    certbot python3-certbot-nginx \
    git

# Use python3.12 if available, otherwise python3
PYTHON=$(command -v python3.12 || command -v python3)
echo "==> Using Python: $PYTHON"

# --- Create app user ---
echo "==> Creating app user..."
id -u $APP_USER &>/dev/null || useradd --system --create-home --shell /bin/bash $APP_USER

# --- Set up PostgreSQL ---
echo "==> Configuring PostgreSQL..."
DB_PASSWORD=$(openssl rand -base64 24)

sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='buckteeth'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER buckteeth WITH PASSWORD '$DB_PASSWORD';"

sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname='buckteeth'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE buckteeth OWNER buckteeth;"

echo "==> Database password: $DB_PASSWORD"
echo "    (save this — you'll need it for .env)"

# --- Copy app files ---
echo "==> Setting up application in $APP_DIR..."
mkdir -p $APP_DIR
if [ "$(pwd)" != "$APP_DIR" ]; then
    cp -r . $APP_DIR/
fi

# --- Python virtual environment ---
echo "==> Creating Python virtual environment..."
$PYTHON -m venv $APP_DIR/.venv
source $APP_DIR/.venv/bin/activate
pip install --upgrade pip
pip install -e "$APP_DIR"

# --- Build frontend ---
echo "==> Building frontend..."
cd $APP_DIR/frontend
npm ci
npm run build

# --- Create .env ---
echo "==> Creating .env file..."
cat > $APP_DIR/.env <<EOF
DATABASE_URL=postgresql+asyncpg://buckteeth:${DB_PASSWORD}@localhost:5432/buckteeth
ANTHROPIC_API_KEY=SET_YOUR_KEY_HERE
LOG_LEVEL=INFO
EOF

chmod 600 $APP_DIR/.env
chown -R $APP_USER:$APP_USER $APP_DIR

# --- Run migrations ---
echo "==> Running database migrations..."
cd $APP_DIR
sudo -u $APP_USER bash -c "source .venv/bin/activate && alembic upgrade head"

# --- Install systemd service ---
echo "==> Installing systemd service..."
cp $APP_DIR/deploy/buckteeth.service /etc/systemd/system/buckteeth.service
systemctl daemon-reload
systemctl enable buckteeth
systemctl start buckteeth

# --- Install nginx config ---
echo "==> Configuring nginx..."
cp $APP_DIR/deploy/buckteeth.nginx /etc/nginx/sites-available/buckteeth
ln -sf /etc/nginx/sites-available/buckteeth /etc/nginx/sites-enabled/buckteeth
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "============================================"
echo "  Buckteeth is running!"
echo "============================================"
echo ""
echo "  App:      http://$(hostname -I | awk '{print $1}')"
echo "  API docs: http://$(hostname -I | awk '{print $1}')/docs"
echo "  Health:   http://$(hostname -I | awk '{print $1}')/health"
echo ""
echo "  NEXT STEPS:"
echo "  1. Edit $APP_DIR/.env and set your ANTHROPIC_API_KEY"
echo "  2. Restart: systemctl restart buckteeth"
echo "  3. (Optional) Add domain + HTTPS:"
echo "     certbot --nginx -d yourdomain.com"
echo ""
echo "  USEFUL COMMANDS:"
echo "  systemctl status buckteeth    # check status"
echo "  journalctl -u buckteeth -f   # view logs"
echo "  systemctl restart buckteeth   # restart after changes"
echo "============================================"
