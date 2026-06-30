# Infrastructure (Terraform)

Greenfield Terraform stack that provisions a complete GCP backend for the
FastAPI boilerplate: a custom VPC with Private Service Access, private
PostgreSQL (Cloud SQL) and Redis (Memorystore), Secret Manager, Artifact
Registry, a Cloud Build deploy trigger, three Cloud Run services (API,
Celery worker, Celery beat) plus a migration Cloud Run job, and an external
HTTPS load balancer with a Certificate Manager managed certificate.

Every environment-specific value (project, region, names, CIDRs, domain,
machine sizes) comes from `infra/.env` — nothing is hardcoded in the `.tf`
files.

## Prerequisites

- Terraform >= 1.6.0
- `gcloud` authenticated as a principal with project owner/editor rights
  (`gcloud auth application-default login`)
- A GCS bucket for Terraform remote state (create it once, out of band)
- The required GCP APIs enabled on the project: Compute, Service Networking,
  Cloud SQL Admin, Redis, Secret Manager, Artifact Registry, Cloud Run,
  Cloud Build, Certificate Manager, IAM
- The GitHub repository connected to Cloud Build (1st-gen GitHub App
  connection) so the trigger can attach to it

## Fill in your values

```bash
cd infra
cp .env.example .env
# edit .env — set at minimum the uncommented (no-default) variables:
#   TF_STATE_BUCKET, TF_VAR_project_id, TF_VAR_region, TF_VAR_zone,
#   TF_VAR_subnet_cidr, TF_VAR_egress_subnet_cidr, TF_VAR_db_password,
#   TF_VAR_secret_names, TF_VAR_github_owner, TF_VAR_github_repo,
#   TF_VAR_domain
```

`.env` is git-ignored intent — never commit it. The wrapper exports each
`TF_VAR_*` so Terraform picks them up automatically, and injects the state
bucket/prefix at `init` time.

## Run

```bash
./tf.sh init      # configures the GCS backend from TF_STATE_BUCKET/PREFIX
./tf.sh plan
./tf.sh apply
./tf.sh output    # lb_ip, dns_authorization_record, urls, etc.
```

## After apply

1. Read `dns_authorization_record` from the outputs and publish the CNAME at
   your DNS provider so the managed certificate can validate.
2. Point your domain's A record at `lb_ip`.
3. Populate the Secret Manager secret versions out of band, e.g.
   `echo -n "<value>" | gcloud secrets versions add app-secret-key --data-file=-`.
4. Push to the configured branch to let Cloud Build build and deploy the
   real container image (the initial image tag only seeds the resources;
   Terraform ignores image drift thereafter).

## What gets created

| Module | Resources |
|--------|-----------|
| `network` | Custom VPC, primary + egress subnets, PSA range + connection, deny-all + allow-PSA egress firewall rules |
| `iam` | Runtime + CI/CD service accounts and their scoped roles |
| `secrets` | Secret Manager containers + per-secret runtime accessor IAM |
| `cloud_sql` | Private PostgreSQL instance, database, user |
| `memorystore` | Private Redis instance (AUTH + transit encryption) |
| `artifact_registry` | Docker repository with cleanup policy |
| `cloud_build` | GitHub push trigger running `cloudbuild.yaml` |
| `cloud_run_job` | Migration job (Direct VPC Egress) |
| `cloud_run_service` (x3) | API (public via LB), worker, beat (internal) |
| `lb_serverless_neg` | HTTPS LB, serverless NEG, managed cert with DNS auth |
