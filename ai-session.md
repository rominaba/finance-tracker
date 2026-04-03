## Session 1: Debugging DigitalOcean Kubernetes Authentication in GitHub Actions
### Prompt (we sent to AI)

After testing the `cicd.yml` workflow on the development branch, GitHub Actions failed around Kubernetes authentication. I submitted the workflow file and the failing section:
```
getting credentials: exec: executable doctl not found

It looks like you are trying to use a client-go credential plugin that is not installed.
```
### AI Response (trimmed)
The AI suggested that doctl must be installed and authenticated before Kubernetes kubeconfig can use DigitalOcean exec-based authentication, and recommended keeping this step in the workflow:

```yaml
- name: Install doctl (required for DOKS kubeconfig exec auth)
  uses: digitalocean/action-doctl@v2
  with:
    token: ${{ secrets.DOCR_TOKEN }}
```
### What Our Team Did With It
- What was useful:
    - It gave us a lead to find out the doctl installation and authentication were required before fetching or using cluster credentials, and where in the cicd.yml file the fix needs to be added.
- What we did with it:
    - We confirmed that the issue was related to DigitalOcean Kubernetes authentication, not the Kubernetes manifests themselves.
- How our team verified, modified, or replaced the suggestion
    -We verified the fix by rerunning the workflow and confirming that deployment steps could authenticate successfully against the DOKS cluster.

---
## Session 2: Dockerfile for Backend+PostgreSQL Evaluation

### Prompt 1 (we sent to AI)
If we want to have 2 db replicas, what would we do?
### AI Response 1 (trimmed)
With your current k8s/02-db.yaml, you should not just set replicas: 2 and call it done.

That would create 2 independent Postgres pods, not a synchronized primary/replica pair.

If you want 2 DB replicas properly, do this:

Use a Postgres HA solution (recommended: a Kubernetes Postgres operator like CloudNativePG, or a HA Helm chart).
Run 1 primary + 1 replica (or 1 primary + 2 replicas for better failover).
Keep separate service endpoints for write vs read traffic.
Keep PVC per pod (already aligned with StatefulSet pattern).
Add failover handling (operator-managed promotion).
For this course deliverable, 1 Postgres pod + PVC is usually sufficient unless HA is explicitly required. If you want, I can draft the exact manifests for a safe primary + replica setup next.

### Prompt 2 (we sent to AI)
 
can you just show me what that would look like out of curiosity? we may not add it so just show it here.

### AI Response 2 (trimmed)
Yep. A clean way is to use a Postgres operator (example: CloudNativePG) and run instances: 2 (1 primary, 1 replica).
```
# 1) App user secret
apiVersion: v1
kind: Secret
metadata:
  name: finance-db-app
  namespace: finance-tracker
type: Opaque
stringData:
  username: finance_user
  password: change-me
---
# 2) Superuser secret
apiVersion: v1
kind: Secret
metadata:
  name: finance-db-superuser
  namespace: finance-tracker
type: Opaque
stringData:
  username: postgres
  password: change-me-too
---
# 3) HA Postgres cluster (1 primary + 1 replica)
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: finance-db
  namespace: finance-tracker
spec:
  instances: 2
  imageName: ghcr.io/cloudnative-pg/postgresql:16
  superuserSecret:
    name: finance-db-superuser
  bootstrap:
    initdb:
      database: finance_db
      owner: finance_user
      secret:
        name: finance-db-app
  storage:
    storageClass: do-block-storage
    size: 10Gi

Backend would use the operator-created service:
- writes: finance-db-rw
- reads: finance-db-ro
```
So DB_HOST becomes finance-db-rw for normal app traffic.

This is the “real” 2-replica pattern, unlike a plain StatefulSet with replicas: 2 (which is not automatic replication/failover by itself).

### What Our Team Did With It
- What was useful:
    - It helped us explore the possibility of creating multiple database replicas.
    - It showed us the scope of the work to make it happen.
- What was incorrect, misleading, or not applicable to our project:
    - This wasn't applicable in general because we decided not to pursue high availability as an advanced feature, as we had already completed 2 advanced features. 
- How our team verified, modified, or replaced the suggestion:
    - We investigated the mentioned solution (using CloudNativePG), but our goal was to make our database durable rather than highly available, so we opted to stay with backup & recovery as one of our advanced features instead.

---

## Session Title 3: Input Validation for Email During Registration
 
### Prompt (we sent to AI)
 
Use some pattern matching or regex for email validation.
 
### AI Response (trimmed)
 
Good idea 👍. A simple regex email check is still lightweight but better than just checking for @.

You don’t need a crazy RFC-compliant regex — just something clean that catches obvious mistakes.

Add Regex Email Validation
Update your validation function in login.js.

Replace:
```
function isValidEmail(email) {
  return email.includes("@");
}
```
with:
```
function isValidEmail(email) {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return pattern.test(email);
}
What this regex checks
^[^\s@]+      -> at least one character before @
@             -> the @ symbol
[^\s@]+       -> at least one character after @
\.            -> a dot
[^\s@]+$      -> domain suffix
```
Examples:

Email	Result
test@example.com
	✅ valid
user123@gmail.ca
	✅ valid
test@	❌ invalid
@gmail.com	❌ invalid
test@gmail	❌ invalid
test@@gmail.com	❌ invalid

### What Our Team Did With It
- What was useful:
    - It helped to provide an alternative to using another built-in library.
- What was incorrect, misleading, or not applicable to our project:
    - There was nothing incorrect or misleading as it did provide the output we wanted.
- How our team verified, modified, or replaced the suggestion:
    - We did testing for the input validation and the regex was working correctly.
