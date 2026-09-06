# Peblo TV

Peblo TV is a streaming platform CMS and Viewer built for production scale.
It consists of a FastAPI backend (PostgreSQL + SQLAlchemy), a React CMS for managing content and publishing, and a React Viewer for end-users to consume published content.

## Architecture & Setup
- **PostgreSQL Database:** Fully relational, using Async SQLAlchemy 2.0. SQLite is restricted strictly to an in-memory testing override.
- **Docker Compose:** Fully containerized setup. Start everything via `docker-compose up --build`.

## Tradeoffs
- A monolithic FastAPI backend was chosen over microservices to minimize deployment complexity and optimize data integrity.
- Client-side data fetching uses `react-query` with a traditional REST API instead of GraphQL to leverage simple caching and predictable SQL querying.

## Immutable Publishing
Content is published via atomic JSON artifacts. The backend computes a deterministic SHA-256 hash of the canonical JSON (collapsing language variants and grouping Season 0 as Trailers) and securely stores it as an immutable artifact in object storage. The active catalogue pointer is then atomically updated in the database to prevent partial state errors.

## Storage
Images and catalogues are managed through an abstraction layer. It supports a `Local` driver for dev, and a Cloudflare `R2` object storage driver (via boto3 S3 API) for production.

## Search
The Viewer implements server-side searching through the `/api/catalogue/search` endpoint instead of downloading the catalogue locally, allowing for scalable DB-side querying and filtering.

## Testing & CI
GitHub Actions is configured to run `pytest` for the backend, as well as `npm run lint`, `typecheck`, and `build` for both React frontends.

## Running Locally

Requirements:
- Docker and Docker Compose

1. Clone the repository.
2. Run `docker-compose up --build`
3. Access the applications:
   - Viewer: `http://localhost:3001`
   - CMS: `http://localhost:3000` (Login with `admin@peblo.local` / `admin123`)
   - API: `http://localhost:8000`
