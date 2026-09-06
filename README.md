# Peblo TV Mini

> A production-minded content operations and publishing platform for managing, validating, publishing, and serving a streaming catalogue.

Peblo TV Mini separates **editorial content management** from the **published consumer catalogue**.

### Stack

- **CMS:** React + TypeScript
- **API:** FastAPI + PostgreSQL + SQLAlchemy
- **Viewer:** React + TypeScript
- **Storage:** Local provider / Cloudflare R2
- **Migrations:** Alembic
- **CI:** GitHub Actions
- **Runtime:** Docker Compose

---

## Architecture

```text
                    ┌──────────────────────┐
                    │         CMS          │
                    │  React + TypeScript  │
                    └──────────┬───────────┘
                               │ REST
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │ Auth · RBAC · CRUD   │
                    │ Validation · Search  │
                    │ Publishing Pipeline  │
                    └───────┬───────┬──────┘
                            │         │
                   ┌────────▼───┐   ┌▼──────────────┐
                   │ PostgreSQL │   │ Object Storage│
                   │ SQLAlchemy │   │ Local / R2    │
                   └──────┬─────┘   └───────────────┘
                          │
                          ▼
               ┌──────────────────────────┐
               │   Immutable Catalogue    │
               │ Canonical JSON + SHA-256 │
               │    Atomic Activation     │
               └────────────┬─────────────┘
                            │
                            ▼
                    ┌──────────────────────┐
                    │       Viewer         │
                    │  React + TypeScript  │
                    │ Browse · Search      │
                    │ Filters · Details    │
                    └──────────────────────┘
```

**Core boundary:** PostgreSQL stores editorial state; the Viewer consumes only the currently active published catalogue.

---

## Core Engineering Decisions

### 1. Immutable & Atomic Publishing

Publishing is a controlled pipeline rather than a direct file overwrite:

```text
Validate
   ↓
Select publishable content
   ↓
Collapse language variants
   ↓
Deterministic ordering
   ↓
Canonical JSON
   ↓
SHA-256 hash
   ↓
Immutable artifact
   ↓
Atomic activation
```

Only content that passes blocking validation and satisfies publishability requirements is included in a catalogue.

Catalogue artifacts are content-addressed using their SHA-256 hash. The active catalogue pointer changes only after the new artifact has been completely written and validated.

If publishing fails, the previously active catalogue remains available.

**Failed publish ≠ broken viewer.**

---

### 2. Backend-Enforced Validation

Validation is enforced server-side rather than trusting the client.

Artwork validation inspects the actual image bytes and enforces:

- Poster: `600 × 900`
- Banner: `1280 × 720`
- Thumbnail: `640 × 360`
- Maximum size: `200 KB`

The validation engine returns stable rule IDs with editor-readable messages, including:

- `SHOW_MISSING_SECTION`
- `EPISODE_MISSING_DURATION`
- `ARTWORK_INVALID_DIMENSIONS`
- `DUPLICATE_CONTENT_GROUP_LANGUAGE`

---

### 3. Language Variants & Season 0

Episodes sharing a `content_group` represent language variants of the same logical episode.

```text
Episode A — English ┐
                    ├── One catalogue episode
Episode A — Hindi   ┘
```

The published catalogue contains one logical episode with a deterministic `languages` array.

Season `0` is treated as **Trailers** and excluded from the normal season experience.

---

### 4. Storage Abstraction

Application logic depends on a storage interface rather than a vendor-specific implementation:

```text
StorageProvider
├── LocalStorageProvider
└── R2StorageProvider
```

Local storage keeps development simple, while Cloudflare R2 provides the production object-storage implementation through its S3-compatible API.

Switching providers is configuration-driven rather than coupled to publishing logic.

---

### 5. Search & Performance

Catalogue search and filtering are performed server-side.

Supported filters compose across:

- query
- category
- language
- section

The frontend uses cached server-state queries, debounced search, pagination, lazy-loaded artwork, skeleton states, and reserved image dimensions to keep interaction responsive and reduce unnecessary rendering and layout shifts.

At larger catalogue volumes, the search layer can evolve toward PostgreSQL full-text search or a dedicated search index without changing the Viewer contract.

---

### 6. Security & Access Control

Authentication and authorization are enforced by the API.

- **Editor:** content management
- **Admin:** privileged administrative and publishing operations

RBAC is enforced server-side; UI visibility is never treated as a security boundary.

Secrets are supplied through environment variables and excluded from version control.

---

## Testing & Quality Gates

The repository includes backend tests focused on high-risk validation and publishing logic, plus frontend linting, type checking, and production builds.

CI runs:

```text
Backend
├── pytest
└── ruff

CMS
├── lint
├── typecheck
└── build

Viewer
├── lint
├── typecheck
└── build
```

---

## Running Locally

### Requirements

- Docker
- Docker Compose

```bash
git clone https://github.com/Miyyapuram-Harshith/peblo.git
cd peblo
docker compose up --build
```

Applications:

| Service | URL |
|---|---|
| Viewer | http://localhost:3001 |
| CMS | http://localhost:3000 |
| API | http://localhost:8000 |

### Demo Admin

```text
Email: admin@peblo.local
Password: admin123
```

Demo credentials are intended for local assessment only. Production deployments must provide secrets through environment configuration.

> **Verification note:** Docker/PostgreSQL container runtime was not executed in the development environment used for this submission. Docker Compose configuration and PostgreSQL migrations are included, but containerized runtime verification remains an environment limitation.

---

## Trade-offs & Scope

A **modular monolith** was chosen instead of microservices because the workload is dominated by transactional content management and publishing rather than independently scalable domains. This keeps deployment and operational complexity low while preserving clear **module boundaries**.

The Viewer uses **REST + cached server-state queries** instead of GraphQL because the catalogue API has a small, explicit read contract and does not require GraphQL's additional runtime complexity.

A **pre-published catalogue** was chosen instead of reconstructing the catalogue from PostgreSQL on every Viewer request. This adds a publishing step but provides deterministic snapshots, a stable read model, fast consumption, and safer failure behavior.

Distributed queues, Redis, Kafka, Kubernetes, and dedicated search infrastructure were intentionally not introduced because they would add operational complexity without proportional value at this scale.

---

## AI-Assisted Development

AI tools were used as development assistants for implementation, refactoring, debugging, and review.

Generated output was **reviewed, tested, corrected, and selectively accepted**. Architectural decisions, security boundaries, publishing semantics, trade-offs, and final implementation were validated against the challenge requirements rather than accepted blindly.

---

## Submission Snapshot

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · React · TypeScript · TanStack Query · Docker · GitHub Actions

**Focus:** validation · RBAC · immutable publishing · deterministic catalogues · storage abstraction · server-side search · responsive UX · operational safety
