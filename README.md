# Finance Tracker Startup Guide

This project runs with Docker Compose, and starts the API, Postgres, and frontend together.

## Prerequisites
- Docker Desktop

## Quick Start
1. Create your local env file by copying .env.example.
2. Fill in values and rename your copy to `.env`.
3. Start everything:
   - `docker compose up --build`

## Service URLs
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`
- Postgres: `localhost:5432`

## Shutting Down
- Stop containers: `docker compose down`
- Stop and remove DB data volume: `docker compose down -v`
