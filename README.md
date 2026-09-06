# Peblo TV

Peblo TV is a streaming platform CMS and Viewer built for production scale.
It consists of a FastAPI backend (PostgreSQL + SQLAlchemy), a React CMS for managing content and publishing, and a React Viewer for end-users to consume published content.

## Architecture Highlights
- **PostgreSQL Database:** Fully relational, using Async SQLAlchemy 2.0.
- **Strict RBAC:** Role-based access control (Admin, Editor) via JWTs.
- **Immutable Publishing:** Content is published via atomic JSON artifacts.
- **Robust Artwork Validation:** Images are inspected byte-by-byte for size, exact dimensions, and valid formats (Pillow).
- **R2 Storage:** Supports both local and Cloudflare R2 object storage.
- **Docker Compose:** Fully containerized setup for easy deployments.

## Running Locally

Requirements:
- Docker and Docker Compose

1. Clone the repository.
2. Run `docker-compose up --build`
3. Access the applications:
   - Viewer: `http://localhost:3001`
   - CMS: `http://localhost:3000` (Login with `admin@peblo.local` / `admin123`)
   - API: `http://localhost:8000`

## Testing
CI automatically runs Pytest for backend and TypeScript/Linting for frontends via GitHub Actions.
