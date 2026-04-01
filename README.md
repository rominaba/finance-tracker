# Finance Tracker
Finance Tracker is a cloud-based personal finance application designed to help individuals better oversee their finances. It targets users seeking a centralized, accessible view of their accounts, transactions, and balances. The system enables users to record and manage income and expenses while monitoring balances in real time. The application consists of three containerized services orchestrated by Kubernetes and deployed on DigitalOcean. Transaction data is stored in a PostgreSQL database with persistent block storage to ensure durability, while replicated backend services enhance availability. Prometheus, Grafana, alerts, and health endpoints enable monitoring system performance and resource usage.

## Repository Structure

- `app/`: Backend API service and backend-specific implementation details. See [`app/README.md`](app/README.md).
- `frontend/`: Frontend web application source and usage details. See [`frontend/README.md`](frontend/README.md).
- `k8s/`: Kubernetes manifests and deployment/operations guidance. See [`k8s/README.md`](k8s/README.md).
- `backup-restore/`: Backup and restore workflows and scripts. See [`backup-restore/README.md`](backup-restore/README.md).

# Finance Tracker Startup Guide

## Local development (Docker Compose)

Use this path to run the stack on your machine: Docker Compose builds and starts the API, Postgres, and frontend together with `localhost` URLs.

### Prerequisites

- Docker Desktop

### Quick start

1. Create your local env file by copying `.env.example`.
2. Fill in values and rename your copy to `.env`.
3. Start everything:
   - `docker compose up --build`

### Service URLs

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`
- Postgres: `localhost:5432`

### Shutting down

- Stop containers: `docker compose down`
- Stop and remove DB data volume: `docker compose down -v`

## Deployment on DigitalOcean (Kubernetes)

Production-style deployment is **not** Docker Compose on a single host. Instead, the app runs on a **DigitalOcean Kubernetes (DOKS)** cluster using the manifests under `k8s/`. Images are typically pulled from **DigitalOcean Container Registry**, the database and volumes use **DO block storage**, and traffic is exposed via **Ingress** (and optional monitoring stacks like Prometheus/Grafana). `kubectl` and `doctl` will be used against the cluster rather than `docker compose`.

For prerequisites, apply order, and operations, see [`k8s/README.md`](k8s/README.md).



