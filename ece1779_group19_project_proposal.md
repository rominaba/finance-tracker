## 1\. Motivation

Most people don’t have a simple, consistent system for understanding the flow of money in and out of their accounts. They rely on spreadsheets or scattered bank views, which makes it hard to reliably budget and make long-term plans. To help support this, we propose a highly available personal finance service that can be reliably accessed like an online banking dashboard, which is the kind of use case cloud-native systems are built to support. 

Our primary users will be individuals who want a centralized view of their accounts and transactions, with the ability to access this information from any device and have it persisted on the web. 

Currently, there are several solutions of this type. Two of these are Quicken and Monarch, which are personal finance products that support budgeting and spending tracking. However, they both have subscription-based pricing models, making them inaccessible to people who would otherwise benefit from a financial management app. Additionally, for Quicken in particular, users often complain about bugs making the software less functional, such as invoice line-items going missing or lists of customers disappearing. These are problems that we aim to show can be solved by applying lessons learned in this course about replication and persistent data. 

## 2\. Objective and Key Features

#### 2.1 \- Project Objective

A core focus of this project is creating a durable, highly available financial tracking product using JavaScript for the frontend and Python for the APIs. Data should never be lost after it is committed, and it should remain responsive to user requests even if individual replicas fail. The application enables users to record their expenses and income, monitor budgets, and understand their financial behaviour.

#### 2.2 \- Core Features

**Orchestration Approach**  
* DigitalOcean (DO) Kubernetes

  * Deployment for the backend services  
  * Persist Volume for PostgreSQL

**Database Schema and Persistent Storage**

* PostgreSQL for storing users, transactions and budgets  
* Persistent volume storage (DigitalOcean Volume)

**Deployment Provider**

* Deploy to DigitalOcean

**Monitoring Setup**

* Utilize the metrics provided by DigitalOcean.
  * Per-Node Metrics
    * CPU  
    * Memory  
    * Disk  
  * Per-Pod Metrics  
    * CPU usage per pod  
    * Memory usage per pod  
    * Restart count  
    
  Which can be utilized in different ways, including:  
  * Show restart count increases  
  * Show cluster remains healthy  
* Alerts: Send emails when certain thresholds are exceeded. 
  1. CPU usage \> 80%  
  2. Memory usage \> 85%  
  3. Pod restart count \> 1  
  4. Disk usage \> 70%  
* Utilize DO’s dashboards in the demo and report.
  * Backend CPU graph  
  * Memory graph  
  * Restart graph  
* Utilize Kubernetes, applications, and droplet logs in the report and demo  
* Potentially 
  * Add:  
    * `/health` endpoint  
    * Structured logging  
    * Prometheus metrics endpoint `/metrics`  
  * Display on frontend dashboard:  
    * “backend healthy”  
    * “DB connected”

**Advanced Features**

We have chosen the following advanced features as they suit the needs of a financial tracking app:

- **Backup and Recovery:** We can take a dump of the PostgreSQL database every day (using some scheduled job) and store it in Spaces Object Storage. This way, if the DB gets corrupted or deleted, we can restore it from Digital Ocean.  
- **Security Enhancements:** We can implement user authentication when users log in to the system. Passwords and financial data will be stored securely using hashing and encryption techniques. Additionally, each user’s financial data will be isolated to maintain privacy.

If we have time, we will also attempt to implement one of the following:

- **Real-time Functionality:** Use WebSockets for live dashboard updates as transactions happen.  
- **CI/CD Pipeline:** Use GitHub Actions for testing and deployment.

#### 2.3 \- Course Requirements

We aim to meet the requirements by creating a Dockerized, stateful application. It will include the following elements from the project guidelines:

* a PostgreSQL database to hold the user’s financial information and transactions,  
* deployment on DigitalOcean with Kubernetes for orchestration,  
* CRUD operations to support transactions,  
* monitoring via DigitalOcean’s tooling,  
* daily backups from PostgreSQL,   
* user authentication,  
* hashing/encryption for sensitive financial data and passwords

#### 2.4 \- Scope and Feasibility

The scope of the project is to implement the above core technical features along with the stated advanced features of backup and recovery and security enhancements, and we expect this to be feasible. Based on the progress and timelines, it may not be entirely feasible to complete the additional features of real-time functionality and CI/CD pipelines. 

## 3\. Tentative Plan

	  
**Task delegation:**  
Member A (Romin Bahrami): Backend & Auth (Python API)  
Member B (Mohammad Harun): Database & Data Durability  
Member C (Brendan Hu): DevOps & Cloud (Docker, Kubernetes, DO)  
Member D (Bobby Li): Frontend & Demo UX (JavaScript)

#### Week 1 \- Architecture \+ Local Minimum Viable Product (MVP): (Docker Compose)

Goal: Working local system with PostgreSQL \+ CRUD \+ Auth using Docker Compose.

Member A \- Backend

* Set up a Flask project  
* Implement:  
  * User registration/login  
  * Password hashing (argon2)  
  * JSON Web Token (JWT) authentication for user login:  
    * After login, servers sends a signed token  
      * Users send the token with each request  
      * Server verifies signatures  
* Create CRUD endpoints:  
  * Create transaction  
  * Read transactions  
  * Update transaction  
  * Delete transaction  
* Connect backend to PostgreSQL

Deliverable: Backend runs locally and connects to the DB container.

Member B \- Database

* Design schema:  
  * users  
  * accounts  
  * transactions  
  * categories  
* Add constraints \+ indexes.  
* Set up migrations (Alembic for Python or similar) 
  * Migrations allow:  
    * Version control DB changes  
    * Apply schema updates safely  
    * Reproduce the schema on new deployments  
* Configure PostgreSQL in Docker Compose  
* Ensure durable configuration (fsync enabled, WAL default)  
  * We need to make sure that once data is committed, it is never lost.  
    PostgreSQL’s default setting ensures this via:  
    * Write Ahead Log (WAL): Before writing data permanently, it writes it to a log file, so if the DB crashes, it can recover data from the log.  
    * fsync: Ensures data is written on disk, not just the memory.

Deliverable: Schema finalized and migrations working.

Member C \- DevOps

* Create:  
  * Backend Dockerfile  
  * Frontend Dockerfile (basic stub)  
  * docker-compose.yml (app \+ postgres)  
* Set up environment variable management  
* Document local startup procedure

Deliverable: Entire app runs via: docker-compose up

Member D \- Frontend

* Create a basic JS frontend  
* Implement:  
  * Login/Register page  
  * Transactions page (list \+ add form)  
* Connect frontend to backend API  
* Basic validation

Deliverable: Users can log in and add/view transactions locally.

End of Week 1 Milestone:

* Full MVP working locally  
* Docker Compose environment is set up  
* Functional Auth \+ CRUD in place

#### Week 2 \- Kubernetes \+ DigitalOcean Deployment

Goal: Live deployment with persistent storage \+ multiple replicas.

Member C \- Kubernetes Setup

* Create DigitalOcean Kubernetes cluster (DOKS)  
* Push Docker images to DO Container Registry  
* Create:  
  * Deployment for backend (2 replicas: so if one fails, the traffic gets routed to the latter)  
  * Service for backend  
  * Deployment for frontend  
  * Ingress (public access)  
* Deploy PostgreSQL using:  
  * StatefulSet (since databases need stable storage and identity, we use StatefulSet instead of Deployment).  
  * PersistentVolumeClaim (PVC): A request for permanent storage `and` attaching a DO Block Storage volume

Deliverable: App accessible via public URL.

Member B \- Database Durability

* Verify PostgreSQL uses a persistent volume  
* Test:  
  * Create transaction  
  * Delete DB pod  
  * Ensure data persists  
* Document durability demonstration steps  
* Add DB connection pooling config

Deliverable: Proven persistence after pod restart.

Member A \- Production Readiness

* Add:  
  * Input validation  
  * Error handling  
  * Logging  
  * Health endpoints (/health)  
* Add readiness & liveness probes

Deliverable: App resilient to pod restarts.

Member D \- Frontend Deployment

* Update frontend to use production API URL  
* Improve UX minimally  
* Add basic dashboard summary

End of Week 2 Milestone: Having a stateful app with persistent storage and high availability:

* Live Kubernetes deployment  
* Backend scaled to 2 replicas  
* PostgreSQL persistent storage verified  
* App survives pod failure

#### Week 3 \- Advanced Features (Security \+ Backups \+ WebSockets/CI/CD)

Goal: Implement required advanced features.

Member B \- Advanced Feature 1 (Durability: Backup and Restore)

* Create K8s CronJob:  
  * Daily pg\_dump  
* Store backups in:  
  * DO Spaces (preferred since it’s not stored in the same storage system)  
    Or  
  * Persistent Volume  
* Write restore script:  
  * Spin new DB pod  
  * Restore from dump  
* Prove Recovery works:  
  * Create transactions  
  * Take backup  
  * Delete DB pod  
  * Restore from the backup file  
  * Show transactions are back

Deliverable: Documented recovery procedure.

Member C \- Advanced feature 2 (CI/CD Pipeline)

* Set up GitHub Actions:  
  * Run tests  
  * Build Docker images  
  * Push to registry  
  * Deploy to Kubernetes  
* Add a separate staging branch if possible

Deliverable: Automatic deployment on push.

Member A \- Advanced Feature 3 (Optional but Strong: Security Hardening)

* Enforce HTTPS (Ingress \+ cert-manager if possible)  
* Move secrets to Kubernetes Secrets  
* Improve the auth token expiration  
* Add rate limiting (basic)

Member D

* Improve UI polish  
* Add confirmation dialogues:  
  E.g., before deleting a transaction, ask to confirm.  
* Improve error handling UX.  
* Prepare a step-by-step demo script like:  
  1. Login  
  2. Add transaction  
  3. Show database  
  4. Delete DB pod  
  5. Restore backup  
  6. Show recovered data

End of Week 3 Milestone:

- Automated backups  
- Restore tested  
- WebSockets/CI/CD working  
- Production-ready security

#### Week 4 \- Monitoring, Failure Testing & Finalization

Goal: Polish, test failure scenarios, and prepare demo/report.

Member A

* Improve backend logs  
* If feasible: Add `/metrics` endpoint

Member B

* Stress test DB:  
  * High insert volume  
  * Verify no data loss  
* Validate backup integrity

Member C

* Configure DigitalOcean monitoring dashboards  
* Set alerts:  
  * High CPU  
  * Pod restart  
* Capture screenshots

Member D

* Final UI polish  
* Create demo script  
* Help record a demo video

#### Final Demo Must Show:

1. User logs in  
2. Creates transactions  
3. Kill backend pod → app still works  
4. Kill DB pod → data still there  
5. Restore from backup  
6. Show monitoring dashboard  
7. Show WebSockets/CI/CD pipeline (if implemented)

## 4\. Initial Independent Reasoning (Before Using AI)

#### 4.1 \- Architecture Choices

After our first meeting, we made the following decisions:

* We would like to use Kubernetes as it is a widely applicable technology that we would like exposure to.  
* Thus, given the complications with running Fly Kubernetes Service mentioned in the project guidelines, we opted for DigitalOcean as our deployment provider.  
* It also follows that we chose DigitalOcean Volumes for persistent storage.  
* Since PostgreSQL is the required method of relational data persistence, we didn’t have to make a decision here.

#### 4.2 \- Anticipated Challenges

**Kubernetes Learning Curve**  
We expect it to take a significant amount of time to properly utilize Kubernetes for orchestration, as we aren’t overly familiar with it, and this is likely to require at least a bit of debugging.

**Stress Testing DB Persistence**  
The PostgreSQL state has to survive replicas crashing and redeployments. Proper testing will be required to make sure this is the case.

**Advanced Features Implementations (WebSockets/CI/CD Pipelines)**  
We expect that advanced features implementations could be challenging, especially real-time updates using WebSockets as WebSockets is new to the team, extra time and challenges can be expected.

#### 4.3 \- Early Development Approach

We created four roles that mirror common roles in industry, and then divided these tasks based on familiarity with the technologies involved and our interest in each. We also divided the work into weeks to prioritize core technical requirements first and give ourselves time to complete the advanced features by the time of the demo.

## 5\. AI Assistance Disclosure

### 5.1 \- AI Tool Contribution

The motivation (except for the comparison to other similar products) and core requirements were decided upon by us as a group. All final design decisions concerning which technologies we used and how to divide the work were also agreed upon as a group.

### 5.2 \- AI Tasks

AI was used mostly for researching and comparison purposes:

* Used ChatGPT (motivation) to help find other similar solutions (Quicken, Monarch) and summarize what they do/possible limitations.  
* Used ChatGPT to research some features, compare properties of different components or options to make design decisions. For instance:  
  * Exploring common hashing methods (bcrypt/argon2) 

### 5.3 \- AI Influence Example

An instance where AI influenced our proposal was when we used ChatGPT to explore options for database backups. It suggested solutions such as DigitalOcean Spaces and Persistent Volumes and provided an overview of their functionalities and typical use cases.

After reviewing these options as a team, we evaluated additional considerations, including reliability and ease of integration. While Persistent Volumes offered tight integration within our containerized environment, we recognized potential limitations in durability and flexibility. Ultimately, we concluded that DigitalOcean Spaces would be a more suitable choice for our use case, given its object storage model and durability.