# Database Backup & Restore System (Kubernetes)

- **Backups** are automated using a Kubernetes **CronJob**
- **Restores** are performed using a Kubernetes **Job**
- Backup files are stored in **DigitalOcean Spaces (S3-compatible storage)**

---

## Backup and Restore System 
Backups run automatically every hour using a CronJob.

### What happens:
1. Database is dumped using `pg_dump`
2. File is compressed (`.sql.gz`)
3. Uploaded to DigitalOcean Spaces:
   - `backup-<timestamp>.sql.gz`
   - `latest.sql.gz`

Note: DB must be empty to have a clean restore.

### Restore Commands
1. Exec into DB: 
```
DB_USER=$(kubectl get secret finance-tracker-secrets -n finance-tracker -o jsonpath="{.data.DB_USER}" | base64 --decode)  
DB_NAME=$(kubectl get secret finance-tracker-secrets -n finance-tracker -o jsonpath="{.data.DB_NAME}" | base64 --decode)  
kubectl exec -it db-0 -n finance-tracker -- psql -U <DB_USER> -d <DB_NAME>  
```
2. Check existing data:  
```
\dt  
SELECT * FROM users;  
```
3. Wipe DB:  
```
\dt  
SELECT * FROM users;  
```
4. Run restore job:
```
kubectl apply -f k8s/db-restore.yaml  
```
5. Monitor restore:  
```
kubectl get jobs -n finance-tracker  
kubectl logs -n finance-tracker job/db-restore  
```
6. Verify restoration:  
ENV vars should still exist from Step 1.  
```
kubectl exec -it db-0 -n finance-tracker -- psql -U <DB_USER> -d <DB_NAME>  
\dt  
SELECT * FROM users;  
```
You should see users that were deleted.  
