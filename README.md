# Holston Electric Scraper Bot

A Python bot that scrapes electricity rates and daily usage from Holston Electric's SmartHub portal, stores data in InfluxDB, and sends Discord notifications.

## Features

- 📊 Scrapes current electricity rates from Holston Electric website
- ⚡ Fetches daily usage data via SmartHub API
- 📈 Stores data in InfluxDB (Cloud or local)
- 🔔 Discord notifications for daily reports and high usage alerts
- 🔄 Runs as a Kubernetes CronJob (6:00 AM daily)

## Local Development

1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

3. Run locally:
```bash
python -m src.main
```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster with ArgoCD
- GitHub Container Registry access
- InfluxDB instance (Cloud or self-hosted)
- Discord webhook URL

### Deploy with ArgoCD

1. Create the secrets in your cluster:
```bash
# Copy and edit the secret template
cp k8s/secret.template.yaml k8s/secret.yaml
# Edit with your actual values
kubectl apply -f k8s/secret.yaml
```

2. Add the application to ArgoCD:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: holston-scraper
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/smileyhogue/HolstonElectricScraping
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Manual Deployment
```bash
kubectl apply -k k8s/
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SMARTHUB_EMAIL` | SmartHub login email |
| `SMARTHUB_PASSWORD` | SmartHub login password |
| `SMARTHUB_SERVICE_LOCATION` | Your service location number |
| `SMARTHUB_ACCOUNT_NUMBER` | Your account number |
| `INFLUXDB_URL` | InfluxDB URL |
| `INFLUXDB_TOKEN` | InfluxDB API token |
| `INFLUXDB_ORG` | InfluxDB organization ID |
| `INFLUXDB_BUCKET` | InfluxDB bucket name |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL |
| `LOG_LEVEL` | Logging level (default: INFO) |

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌───────────┐
│ SmartHub Portal │────▶│   Scraper    │────▶│ InfluxDB  │
│ (Usage Data)    │     │   (Python)   │     │ (Storage) │
└─────────────────┘     └──────┬───────┘     └───────────┘
                               │
┌─────────────────┐            │
│ holstonelectric │────────────┘
│ .com (Rates)    │            │
└─────────────────┘            ▼
                        ┌───────────┐
                        │  Discord  │
                        │ (Alerts)  │
                        └───────────┘
```
