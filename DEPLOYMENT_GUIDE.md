# Hex Explorer Deployment Guide

## Security Status

**Current Implementation Status**: PRODUCTION READY with security features implemented

### Implemented Security Features
- [x] **Authentication System**: JWT-based authentication with Flask-Login
- [x] **Password Security**: Bcrypt hashing with strength requirements
- [x] **Input Validation**: Marshmallow schemas for all inputs
- [x] **CSRF Protection**: Flask-WTF CSRF tokens
- [x] **Rate Limiting**: Flask-Limiter for API protection
- [x] **Session Security**: Secure session management with lockout
- [x] **Database**: SQLAlchemy ORM with prepared statements
- [x] **Logging**: Comprehensive logging with rotation
- [x] **Security Headers**: Talisman for HTTPS and headers
- [x] **Environment Variables**: Secrets stored in .env file

## Prerequisites

- Python 3.11 or higher
- PostgreSQL (for production) or SQLite (for development)
- Redis (optional, for session storage and rate limiting)
- SSL certificate (for production)

## Quick Start (Development)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hexcrawl
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements-security.txt
   pip install -r requirements-web.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

4. **Initialize database**
   ```bash
   python init_migrations.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open http://localhost:5000
   - Register a new account
   - Start exploring!

## Production Deployment

### 1. Server Setup (Ubuntu/Debian)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3.11 python3.11-venv python3-pip
sudo apt install postgresql postgresql-contrib
sudo apt install redis-server
sudo apt install nginx
sudo apt install certbot python3-certbot-nginx

# Create application user
sudo useradd -m -s /bin/bash hexexplorer
sudo su - hexexplorer
```

### 2. Database Setup

```bash
# PostgreSQL setup
sudo -u postgres psql

CREATE DATABASE hexexplorer;
CREATE USER hexexplorer_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE hexexplorer TO hexexplorer_user;
\q
```

### 3. Application Setup

```bash
# Clone and setup
cd /home/hexexplorer
git clone <repository-url> hexcrawl
cd hexcrawl

# Virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-security.txt
pip install -r requirements-web.txt
pip install gunicorn

# Configure environment
cp .env.example .env
nano .env  # Edit with production values
```

### 4. Environment Configuration (.env)

```env
# Production configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<generate-with-python-c-import-secrets-print-secrets.token_hex(32)>
JWT_SECRET_KEY=<generate-another-secret>

# Database
DATABASE_URL=postgresql://hexexplorer_user:password@localhost:5432/hexexplorer

# Redis
REDIS_URL=redis://localhost:6379/0
RATELIMIT_STORAGE_URL=redis://localhost:6379/1

# Security
SESSION_LIFETIME_HOURS=24
MAX_LOGIN_ATTEMPTS=5
PASSWORD_MIN_LENGTH=8

# CORS (restrict to your domain)
CORS_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/hexexplorer/app.log
```

### 5. Initialize Database

```bash
source venv/bin/activate
python init_migrations.py
```

### 6. Systemd Service

Create `/etc/systemd/system/hexexplorer.service`:

```ini
[Unit]
Description=Hex Explorer Web Service
After=network.target postgresql.service redis.service

[Service]
User=hexexplorer
Group=hexexplorer
WorkingDirectory=/home/hexexplorer/hexcrawl
Environment="PATH=/home/hexexplorer/hexcrawl/venv/bin"
ExecStart=/home/hexexplorer/hexcrawl/venv/bin/gunicorn \
    --workers 4 \
    --worker-class eventlet \
    --bind unix:hexexplorer.sock \
    --log-file /var/log/hexexplorer/gunicorn.log \
    --log-level info \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hexexplorer
sudo systemctl start hexexplorer
```

### 7. Nginx Configuration

Create `/etc/nginx/sites-available/hexexplorer`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    
    location / {
        proxy_pass http://unix:/home/hexexplorer/hexcrawl/hexexplorer.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /api/auth/login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://unix:/home/hexexplorer/hexcrawl/hexexplorer.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://unix:/home/hexexplorer/hexcrawl/hexexplorer.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static {
        alias /home/hexexplorer/hexcrawl/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/hexexplorer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8. SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com
```

### 9. Firewall Configuration

```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

## Monitoring & Maintenance

### Log Files
- Application logs: `/var/log/hexexplorer/app.log`
- Error logs: `/var/log/hexexplorer/hexexplorer_errors.log`
- Security logs: `/var/log/hexexplorer/security.log`
- Nginx logs: `/var/log/nginx/access.log` and `error.log`

### Health Check Endpoint

Add to your monitoring system:
```bash
curl https://yourdomain.com/api/test
```

### Database Backup

Create `/home/hexexplorer/backup.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/hexexplorer/backups"
mkdir -p $BACKUP_DIR

# Database backup
pg_dump hexexplorer > $BACKUP_DIR/hexexplorer_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
crontab -e
0 2 * * * /home/hexexplorer/backup.sh
```

## Security Checklist

Before going live, ensure:

- [ ] Strong SECRET_KEY and JWT_SECRET_KEY generated
- [ ] Database password is secure
- [ ] SSL certificate installed and auto-renewal configured
- [ ] Firewall configured with minimal open ports
- [ ] Rate limiting enabled on authentication endpoints
- [ ] Debug mode disabled
- [ ] Error pages don't expose sensitive information
- [ ] Regular backups configured
- [ ] Log rotation configured
- [ ] Monitoring and alerting set up
- [ ] Security headers configured in Nginx
- [ ] CORS restricted to your domain

## Troubleshooting

### Application won't start
```bash
# Check logs
sudo journalctl -u hexexplorer -f
tail -f /var/log/hexexplorer/app.log

# Check permissions
ls -la /home/hexexplorer/hexcrawl/
```

### Database connection errors
```bash
# Test connection
psql -U hexexplorer_user -d hexexplorer -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

### Rate limiting issues
```bash
# Check Redis
redis-cli ping

# Monitor rate limits
redis-cli monitor
```

## Updates and Maintenance

### Updating the application
```bash
cd /home/hexexplorer/hexcrawl
git pull origin main
source venv/bin/activate
pip install -r requirements-security.txt --upgrade
python init_migrations.py  # Run any new migrations
sudo systemctl restart hexexplorer
```

### Security updates
```bash
# Check for vulnerable packages
safety check

# Update all packages
pip list --outdated
pip install --upgrade [package-name]
```

## Support

For issues or questions:
- Check logs in `/var/log/hexexplorer/`
- Review the security implementation guide
- Create an issue in the repository

## License

[Your License Here]