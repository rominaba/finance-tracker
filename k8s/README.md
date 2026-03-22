# Kubernetes Manifests

This folder contains manifests used by Kubernetes for orchestration:
- Namespace
- Secret + ConfigMap
- Postgres StatefulSet + Service + PVC
- Backend Deployment (2 replicas) + Service
- Frontend Deployment + Service
- Ingress
- Monitoring (Prometheus + node-exporter)
- Dashboards (Grafana)

### Prerequisites
- Install `kubectl` and confirm it is available:
  - `kubectl version --client`
- Install `doctl` and confirm it is available:
  - `doctl version`
- Authenticate `doctl` to your DigitalOcean account:
  - `doctl auth init`
- Make sure your kube context points to your DOKS cluster:
  - `kubectl config current-context`

### Overview of the Manifests
State Management:
- `k8s/02-db.yaml` defines PostgreSQL db as a StatefulSet.

Persistent Storage:
- `k8s/02-db.yaml` uses a PersistentVolumeClaim with DO block storage (`do-block-storage`) for k8s persistent storage.

Deployment Provider:
- `k8s/02-db.yaml` uses DigitalOcean block storage.
- `k8s/03-backend.yaml` and `k8s/04-frontend.yaml` pull images from DigitalOcean Container Registry.

Orchestration Approach (Option B: Kubernetes):
- Kubernetes manifests in this folder (k8s/*) as described above.

Prometheus Monitoring (CPU + Disk)
- `k8s/06-monitoring.yaml` deploys:
  - `node-exporter` DaemonSet for node-level CPU and disk filesystem metrics
  - `prometheus` Deployment + Service + PVC
  - RBAC + scrape config (kubelet cAdvisor for **container CPU, memory, network**; kubelet resource/volume endpoints for disk where needed)
  - **`finance-tracker-backend-metrics`** job: scrapes each backend pod’s **`/metrics`** when `prometheus.io/scrape: "true"` is set on the pod template (`k8s/03-backend.yaml`)

  Access Prometheus UI:
  ```bash
  kubectl -n finance-tracker port-forward svc/prometheus 9090:9090
  ```
  Open:
  - http://localhost:9090

  Useful PromQL queries:

  CPU usage per node (%):
  ```promql
  100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))
  ```

  Container CPU usage (cores), grouped by pod:
  ```promql
  sum by (namespace, pod) (
    rate(container_cpu_usage_seconds_total{container!="",pod!=""}[5m])
  )
  ```

  Disk usage per node filesystem (%):
  ```promql
  100 * (
    1 - (
      node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} /
      node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}
    )
  )
  ```
Grafana Dashboards (backend/frontend/db)
- `k8s/07-grafana.yaml` deploys Grafana with:
  - Provisioned Prometheus datasource
  - **Finance Tracker - CPU and DB storage** — CPU for backend/frontend/db + DB PVC disk
  - **Finance Tracker - Memory, Network & App** — container memory & network (cadvisor) + **Flask HTTP** metrics (request rate, latency, in-flight) from the backend `/metrics` endpoint

Access Grafana UI:
```bash
kubectl -n finance-tracker port-forward svc/grafana 3000:3000
```

Open:
- http://localhost:3000

Login:
- username: `ft-admin`
- password: `admin321`



### Checks
- Confirm cluster can pull from DOCR:
  - `doctl kubernetes cluster registry add finance-tracker-k8s`

### Set Image Tags
The deployment files currently use `:latest`. For deterministic deploys, set explicit tags:

### Deployment Commands
Once you've used `doctl auth init` and `kubectl config current-context` is `do-tor1-finance-tracker-k8s`, you can redeploy using the following commands:

```
NS=finance-tracker
REGISTRY=registry.digitalocean.com/finance-tracker-registry
# Customized tags requires modifying the corresponding manifests.
TAG=latest

BACKEND_IMAGE=$REGISTRY/finance-tracker-api:$TAG
FRONTEND_IMAGE=$REGISTRY/finance-tracker-frontend:$TAG

docker build -t "$BACKEND_IMAGE" .
docker push "$BACKEND_IMAGE"

docker build -t "$FRONTEND_IMAGE" ./frontend
docker push "$FRONTEND_IMAGE"

kubectl -n "$NS" set image deployment/backend backend="$BACKEND_IMAGE"
kubectl -n "$NS" set image deployment/frontend frontend="$FRONTEND_IMAGE"
```
### Troubleshooting DOCR Push (401 Unauthorized)
If `docker push` fails with:
- `failed to fetch oauth token ... 401 Unauthorized`

Re-authenticate and ensure WSL uses a Docker config without the broken Desktop credential helper.

```bash
mkdir -p ~/.docker-wsl
printf '{"auths":{}}' > ~/.docker-wsl/config.json
export DOCKER_CONFIG=~/.docker-wsl

doctl auth init
doctl registry login --expiry-seconds 36000
```

Retry push:
```bash
docker push "$BACKEND_IMAGE"
docker push "$FRONTEND_IMAGE"
```

### Apply in Order
```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-config.yaml
kubectl apply -f k8s/02-db.yaml
kubectl apply -f k8s/03-backend.yaml
kubectl -n finance-tracker rollout restart deploy/backend
kubectl apply -f k8s/04-frontend.yaml
kubectl -n finance-tracker rollout restart deploy/frontend
kubectl apply -f k8s/05-ingress.yaml
kubectl apply -f k8s/06-monitoring.yaml
kubectl -n finance-tracker rollout restart deploy/prometheus
kubectl apply -f k8s/07-grafana.yaml
kubectl -n finance-tracker rollout restart deploy/grafana
```

### Verify
```bash
kubectl get all -n finance-tracker
kubectl get pvc -n finance-tracker
kubectl get ingress -n finance-tracker
kubectl get pods -n finance-tracker -o wide
kubectl get daemonset -n finance-tracker
kubectl get svc -n finance-tracker
```

Check logs if needed:
```bash
kubectl logs -n finance-tracker deploy/backend
kubectl logs -n finance-tracker statefulset/db
kubectl logs -n finance-tracker deploy/frontend
kubectl logs -n finance-tracker deploy/prometheus
kubectl logs -n finance-tracker deploy/grafana
```
### Ingress Hostnames
`k8s/05-ingress.yaml` is configured for `sslip.io` using the current ingress IP:
- `app.174.138.113.111.sslip.io`
- `api.174.138.113.111.sslip.io`

If the ingress load balancer IP changes, update the hostnames in `k8s/05-ingress.yaml` to match the new IP.