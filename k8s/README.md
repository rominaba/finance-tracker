# Kubernetes Manifests

This folder contains kubernetes manifests for:
- Namespace
- Secret + ConfigMap
- Postgres StatefulSet + Service + PVC
- Backend Deployment (2 replicas) + Service
- Frontend Deployment + Service
- Ingress

## Checks
- Confirm your cluster context:
  - `kubectl config current-context`
- Confirm cluster can pull from DOCR:
  - `doctl kubernetes cluster registry add finance-tracker-k8s`

## Set Image Tags
The deployment files currently use `:latest`. For deterministic deploys, set explicit tags:

```bash
kubectl -n finance-tracker set image deployment/backend \
  backend=registry.digitalocean.com/finance-tracker-registry/finance-tracker-api:<your-tag>

kubectl -n finance-tracker set image deployment/frontend \
  frontend=registry.digitalocean.com/finance-tracker-registry/finance-tracker-frontend:<your-tag>
```

## Troubleshooting DOCR Push (401 Unauthorized)
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

## Apply in Order
```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-config.yaml
kubectl apply -f k8s/02-db.yaml
kubectl apply -f k8s/03-backend.yaml
kubectl apply -f k8s/04-frontend.yaml
kubectl apply -f k8s/05-ingress.yaml
```

## Verify
```bash
kubectl get all -n finance-tracker
kubectl get pvc -n finance-tracker
kubectl get ingress -n finance-tracker
kubectl get pods -n finance-tracker -o wide
```

Check logs if needed:
```bash
kubectl logs -n finance-tracker deploy/backend
kubectl logs -n finance-tracker statefulset/db
kubectl logs -n finance-tracker deploy/frontend
```

## Ingress Hostnames
`k8s/05-ingress.yaml` is configured for `sslip.io` using the current ingress IP:
- `app.174.138.113.111.sslip.io`
- `api.174.138.113.111.sslip.io`

If the ingress load balancer IP changes, update the hostnames in `k8s/05-ingress.yaml` to match the new IP.
