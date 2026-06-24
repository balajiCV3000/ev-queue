# Architecture — EV Charging Queue Optimizer

## Overview

A containerized Flask simulation app deployed on AWS ECS Fargate, fronted by an Application Load Balancer. All infra is provisioned manually; deployments are fully automated via GitHub Actions.

---

## AWS Services

| Service | Role |
|---|---|
| **Amazon ECR** | Stores versioned Docker images (tagged by Git SHA) |
| **Amazon ECS (Fargate)** | Runs the container — single task, single Gunicorn worker |
| **Application Load Balancer** | Accepts inbound HTTP traffic, health-checks `/health`, forwards to the ECS task |
| **IAM** | Scoped credentials in GitHub Secrets authorize CI to push to ECR and update ECS |

---

## Deployment Flow

```
Developer push to master
        │
        ▼
  CI workflow (GitHub Actions)
  ├── Lint (ruff)
  ├── Tests (pytest)
  └── Dependency audit (pip-audit)
        │ pass
        ▼
  Deploy workflow (GitHub Actions)
  ├── Build Docker image
  ├── Push image to ECR  (tagged with commit SHA)
  ├── Register new ECS task definition revision
  ├── Update ECS service  (desired-count 1, force-new-deployment)
  └── Wait for service stability (ALB health checks /health)
```

---

## Runtime Architecture

```
Internet
   │
   ▼
Application Load Balancer  (HTTP :80)
   │
   ▼
ECS Fargate Task  (single task)
└── Gunicorn (1 worker, port 5000)
    └── Flask app
        ├── Simulation engine  (in-process memory)
        ├── Google Maps API    (route generation)
        └── Static assets      (served by Flask)
```

---

## Key Design Decisions

**Single worker / single task** — Simulation state lives in process memory. Running multiple workers or tasks would produce split-brain state. A shared store (Redis, DB) would be needed before scaling out.

**SHA-pinned image tags** — Each ECS task definition revision references an exact image digest, making rollbacks deterministic.

**GitHub Actions as CI/CD** — Deploy only triggers after CI passes on `master`, preventing broken builds from reaching production.

**`/health` endpoint** — ALB health checks gate traffic. Only healthy tasks receive requests; unhealthy tasks are drained and replaced automatically.

---

## Local Development

```bash
cp env.example .env          # set GOOGLE_MAPS_API_KEY, etc.
pip install -r requirements.txt
python app.py                # runs Flask dev server on :5000
```

Key env vars:

| Variable | Purpose |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Required for route generation |
| `BOOTSTRAP_SIMULATION` | `false` for lightweight startup (tests/CI) |
| `APP_ENV` | `production` enables strict startup checks |
| `REQUIRE_MAPS_API_KEY` | `true` causes fast-fail if key is missing |

---

## Constraints & Known Limitations

- State is not persisted — a container restart resets the simulation.
- One ECS task only; horizontal scaling requires externalizing simulation state.
- Google Maps API calls are billed per request; high simulation throughput increases Maps cost.
