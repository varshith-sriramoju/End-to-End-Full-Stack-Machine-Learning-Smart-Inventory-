# SmartInventory - Retail Forecasting Platform

A complete end-to-end inventory forecasting system for retail chain management, featuring machine learning-powered demand prediction, real-time dashboards, and automated retraining capabilities.

## 🚀 Quick Start

```bash
# Clone and start the application
git clone <repository-url>
cd <repo-folder>
docker-compose up --build
```

Access the application at `http://localhost:8000`

## 📋 Overview

SmartInventory provides retail managers with intelligent inventory forecasting capabilities through:
- **Data Upload**: CSV import with validation and processing
- **ML Forecasting**: Gradient boosting models for demand prediction
- **Real-time Dashboards**: Interactive visualizations and KPI monitoring
- **API Integration**: RESTful endpoints for system integration
- **Automated Retraining**: Maintains model accuracy over time

## 🏗 Architecture

### Technology Stack
- **Frontend**: Vite + React + TypeScript + Tailwind CSS
- **Backend**: Django 5.0 + Django REST Framework
- **ML Pipeline**: pandas + scikit-learn + joblib
- **Database**: MySQL with Redis caching
- **Task Queue**: Celery with Redis broker
- **Containerization**: Docker + Kubernetes
- **Monitoring**: Prometheus + Grafana + structured logging

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django API    │    │  ML Pipeline    │
│   Dashboard     │◄──►│   + DRF         │◄──►│  + Celery       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │     MySQL       │    │     Redis       │
                       │   Database      │    │  Cache + Queue  │
                       └─────────────────┘    └─────────────────┘
```

## 🔧 Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend development)

### Frontend Development (Vite + React)

```powershell
# From project root
npm install

# Start dev server (http://localhost:5173 by default)
npm run dev

# If http://localhost:5173 does not load:
# - Try http://127.0.0.1:5173
# - Make sure you run from the project root, not a subfolder
# - Check terminal for errors after running `npm run dev`
# - Try a different browser or an incognito window
# - To bind to all interfaces and auto-open:
#   npx vite --host --port 5173 --open

# Create a production build (outputs to dist/)
npm run build
```

Backend API remains at `http://localhost:8000`.

### Local Development (Full Stack with Docker Compose)

1. **Environment Setup**
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. **Start Services**
```bash
docker-compose up --build
```

3. **Run Migrations**
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

4. **Load Sample Data**
```bash
docker-compose exec web python scripts/generate_sample_data.py
```

## 🐳 Run with Docker (step-by-step)

Follow these steps to run the full stack (MySQL, Redis, Django web, Celery, Celery Beat) using Docker Compose.

1) Prerequisites
- Install and start Docker Desktop
- Ensure these local ports are free: 8000 (web), 3307 (MySQL), 6379 (Redis)

2) From the repository root, build images
```powershell
# Windows PowerShell
docker-compose build
```

3) Start all services
```powershell
docker-compose up
# or run in the background
docker-compose up -d
```

What happens on first start:
- MySQL initializes with database smartinventory2 and user root/root
- Redis starts
- Web waits for healthy MySQL/Redis, then runs: collectstatic, migrate, generate_sample_data (via override), and starts at http://localhost:8000
  - MySQL is published on host port 3307 (container listens on 3306)
- Celery and Celery Beat start and connect to Redis/MySQL

4) Open the app
- Backend (Django): http://localhost:8000
- Frontend dev server (optional, local): http://localhost:5173

5) (Optional) Create an admin user
```powershell
docker-compose exec web python manage.py createsuperuser
```

6) Useful commands
```powershell
# Follow logs
docker-compose logs -f web
docker-compose logs -f db

# Re-seed sample data
docker-compose exec web python scripts/generate_sample_data.py

# Run tests in the container
docker-compose exec web python -m pytest -q

# Stop services
docker-compose down

# Stop and remove volumes (resets MySQL/Redis data and static/media volumes)
docker-compose down -v
```

Troubleshooting:
- If port 3306 is in use, stop any local MySQL server or change the published port in docker-compose.override.yml
- First build can take a few minutes while installing Python dependencies
- If web fails on startup, check db and redis health: `docker-compose ps` and `docker-compose logs -f db redis`

### Environment File Mapping

This project uses multiple environment files to separate concerns:

| File | Purpose | Loaded By |
|------|---------|-----------|
| `.env` | Generic defaults (optional, can be kept minimal) | python-decouple (Django) when present |
| `.env.development` | Development container values (service hostnames: `db`, `redis`) | `docker-compose.yml` via `env_file` |
| `.env.production` | Production / deployment values (external hostnames, secrets via expansion) | `docker-compose.prod.yml` |
| `.env.example` | Template for contributors—copy to create real env files | Humans only |

Frontend (Vite) variables must be prefixed with `VITE_` (e.g. `VITE_API_URL`). These are injected at build/dev time and are not available to Django.

Minimal dev workflow:
```powershell
Copy-Item .env.example .env.development
# Edit .env.development and then:
docker-compose up --build
```

Production build (example):
```powershell
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

If you add new variables required by the application, update `.env.example` so others know they must set them.

## 📊 Data Schema

### CSV Upload Format
```csv
date,store_id,sku_id,sales,price,on_hand,promotions_flag
2023-01-01,STORE001,SKU001,25,9.99,100,0
2023-01-02,STORE001,SKU001,30,9.99,95,1
```

### Required Columns
- `date`: YYYY-MM-DD format
- `store_id`: Store identifier
- `sku_id`: Product SKU
- `sales`: Units sold
- `price`: Unit price
- `on_hand`: Current inventory
- `promotions_flag`: 1 if promotion active, 0 otherwise

## 🔐 Authentication & Authorization

### User Roles
- **Admin**: Full system access, model management
- **Manager**: Store-level access, data upload
- **Analyst**: Read-only access, reporting

### API Authentication
```javascript
// Login
POST /api/auth/login
{
  "username": "manager@store.com",
  "password": "password"
}

// Use JWT token in headers
Authorization: Bearer <jwt-token>
```

## 📡 API Endpoints

### Core Endpoints
```
POST /api/auth/login/          → JWT authentication
POST /api/data/upload/         → CSV upload
GET  /api/data/ingestion/{id}/ → Job status
GET  /api/predict/             → Real-time predictions
POST /api/predict/batch/       → Batch predictions
POST /api/models/retrain/      → Model retraining
GET  /api/models/              → Model versions
```

### Example Usage
```javascript
// Get predictions
const response = await fetch('/api/predict/?sku_id=SKU001&store_id=STORE001', {
  headers: { 'Authorization': 'Bearer ' + token }
});
const predictions = await response.json();
```

## 🤖 Machine Learning Pipeline

### Model Architecture
- **Algorithm**: Gradient Boosting Regressor
- **Features**: Lag variables, rolling averages, seasonality
- **Metrics**: MAE, RMSE, MAPE
- **Retraining**: Automated based on performance degradation

### Training Pipeline
```bash
# Manual training
python scripts/train.py --data-version latest --model-name prod_v1

# Scheduled retraining (via Celery)
docker-compose exec web python manage.py shell
>>> from celery_app.tasks import retrain_models
>>> retrain_models.delay()
```

## 📈 Dashboard Features

### KPI Overview
- Predicted stockouts (next 30 days)
- At-risk SKUs by category
- Inventory turnover rates
- Forecast accuracy metrics

### Interactive Charts
- Historical vs predicted demand
- Store performance comparison
- Seasonal trend analysis
- SKU-level deep dives

## 🚀 Deployment

### Local Development
```bash
docker-compose up --build
```

### Production (Kubernetes)
```bash
kubectl apply -f k8s/namespace.yaml
# Apply your database manifest:
# If using MySQL (preferred):
# kubectl apply -f k8s/mysql.yaml
# If your repo/environment still uses Postgres manifests:
# kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/web.yaml
kubectl apply -f k8s/celery.yaml
```

### CI/CD Pipeline
- **Testing**: Automated unit and integration tests
- **Building**: Docker image creation and registry push
- **Deployment**: Kubernetes rolling updates
- **Monitoring**: Health checks and alerting

## 🔍 Monitoring & Observability

### Health Checks
- `GET /health/` - Application health
- `GET /health/db/` - Database connectivity
- `GET /health/redis/` - Cache connectivity
- `GET /metrics/` - Prometheus metrics

### Logging
Structured JSON logging with correlation IDs:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "smartinventory",
  "correlation_id": "abc-123",
  "message": "Model prediction completed",
  "duration_ms": 45
}
```

## 🧪 Testing

### Run Test Suite
```bash
# All tests
docker-compose exec web python -m pytest

# With coverage
docker-compose exec web python -m pytest --cov=smartinventory --cov-report=html

# Specific test types
docker-compose exec web python -m pytest tests/unit/
docker-compose exec web python -m pytest tests/integration/
```

### Test Categories
- **Unit Tests**: Models, serializers, utilities
- **Integration Tests**: API endpoints, database operations
- **E2E Tests**: Full user workflows

## 📚 Documentation

- **API Documentation**: Available at `/docs/` (Swagger UI)
- **Architecture**: See `docs/architecture.md`
- **Deployment Guide**: See `docs/deployment.md`
- **Contributing**: See `CONTRIBUTING.md`

## 🔧 Configuration

### Environment Variables
```bash
# Database (inside containers)
DATABASE_URL=mysql://root:root@db:3306/smartinventory2

# If connecting from your host (outside containers)
# MySQL is published on localhost:3307 by docker-compose.override.yml

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secret-key
DEBUG=False

# ML Settings
MODEL_RETRAIN_THRESHOLD=0.15
PREDICTION_CACHE_TTL=3600
```

## 📊 Performance

### Benchmarks
- **API Response**: <200ms (95th percentile)
- **Prediction Latency**: <100ms (single SKU)
- **Batch Processing**: 10K SKUs in <5 minutes
- **Data Ingestion**: 1M records in <2 minutes

### Scaling Considerations
- Horizontal pod autoscaling for web tier
- Redis clustering for cache layer
- Database read replicas for analytics
- Celery worker scaling based on queue depth

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: `/docs/` directory
- **API Reference**: `http://localhost:8000/docs/`

---

## 🗄️ Database & Migration Notes (PostgreSQL ➜ MySQL)

This project was migrated from PostgreSQL to MySQL. Key points below; use these as the source of truth for DB setup.

### Summary of changes
- Dependencies: removed `psycopg2-binary`, added `mysqlclient`.
- Django settings: `DATABASE_URL` supports MySQL and enforces utf8mb4 + strict SQL mode.
- Docker/Compose: DB service uses `mysql:8.0` with healthcheck; MySQL published on host port 3307.
- Kubernetes: added `k8s/mysql.yaml`; web deployment configured to use MySQL `DATABASE_URL`.
- CI: updated workflow to use MySQL service and install MySQL client libs.
- Frontend: Vite build validated; `src/App.tsx` and `src/vite-env.d.ts` typed for TS.

### Final database configuration
- Database: `smartinventory2`
- Username: `root`
- Password: `root`

Where it’s set:
- Local env: `DATABASE_URL=mysql://root:root@localhost:3306/smartinventory2`
- Docker Compose (web/celery): `DATABASE_URL=mysql://root:root@db:3306/smartinventory2`
- Kubernetes: `DATABASE_URL=mysql://root:root@mysql-service:3306/smartinventory2`

Optional: create DB/user on an external MySQL server
```sql
CREATE DATABASE smartinventory2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON smartinventory2.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

### Local (without Docker) backend
```powershell
# From project root
python -m pip install --upgrade pip
pip install -r requirements.txt

# Ensure MySQL exists and is utf8mb4, then run:
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver localhost:8000
```

### Validation
- You may see editor warnings until dependencies are installed (pip/npm).
- Frontend build: `npm install` then `npm run build`.
- Tests (inside Docker): `docker-compose exec web python -m pytest -q`.

---

## 🧰 Troubleshooting (common issues)

### White screen / JS bundle not loading
```powershell
# Rebuild frontend assets
npm run build

# Collect static files
python manage.py collectstatic --noinput --clear
```

### API connection issues
```powershell
curl http://localhost:8000/health/
python manage.py dbshell
```

### CORS errors (development)
In `smartinventory/settings.py`, ensure dev CORS is permissive:
```python
CORS_ALLOW_ALL_ORIGINS = True  # Development only
```

### Database migration issues
```powershell
python manage.py migrate --fake-initial
# Or recreate migrations then migrate
```

### Static files missing / unstyled pages
```powershell
python manage.py collectstatic --noinput
```

### Port conflicts
```powershell
# Change dev server port
python manage.py runserver localhost:8001
```

### Docker issues
```powershell
docker-compose build --no-cache
docker-compose logs web
docker-compose logs db
```