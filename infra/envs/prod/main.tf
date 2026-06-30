######################################################################
# Production environment — greenfield FastAPI stack.
#
# Wiring:
#   network    → VPC, subnets, PSA, egress firewall
#   iam        → runtime + cicd service accounts
#   secrets    → Secret Manager containers + runtime accessor
#   cloud_sql  → private PostgreSQL over PSA
#   memorystore→ private Redis over PSA
#   artifact_registry → Docker repo for images
#   cloud_build→ GitHub push trigger
#   cloud_run_job     → migrate job
#   cloud_run_service → api (public via LB) + worker + beat (internal)
#   lb_serverless_neg → HTTPS LB + managed cert for the api
######################################################################

module "iam" {
  source = "../../modules/iam"

  project_id            = var.project_id
  runtime_sa_account_id = var.runtime_sa_account_id
  cicd_sa_account_id    = var.cicd_sa_account_id
  runtime_bucket_names  = var.runtime_bucket_names
}

module "network" {
  source = "../../modules/network"

  project_id            = var.project_id
  region                = var.region
  vpc_name              = var.vpc_name
  subnet_name           = var.subnet_name
  subnet_cidr           = var.subnet_cidr
  egress_subnet_name    = var.egress_subnet_name
  egress_subnet_cidr    = var.egress_subnet_cidr
  psa_range_name        = var.psa_range_name
  psa_prefix_length     = var.psa_prefix_length
  deny_all_egress_name  = var.deny_all_egress_name
  allow_egress_psa_name = var.allow_egress_psa_name
  runtime_sa_email      = module.iam.runtime_sa_email
  db_port               = var.db_port
  redis_port            = var.redis_port
}

module "cloud_sql" {
  source = "../../modules/cloud_sql"

  project_id          = var.project_id
  region              = var.region
  instance_name       = var.sql_instance_name
  database_version    = var.sql_database_version
  tier                = var.sql_tier
  edition             = var.sql_edition
  disk_size           = var.sql_disk_size
  disk_type           = var.sql_disk_type
  availability_type   = var.sql_availability_type
  ssl_mode            = var.sql_ssl_mode
  deletion_protection = var.sql_deletion_protection
  vpc_self_link       = module.network.vpc_self_link
  database_name       = var.db_name
  db_user             = var.db_user
  db_password         = var.db_password

  # Cloud SQL needs the PSA connection established before it can get a
  # private IP in the VPC.
  depends_on = [module.network]
}

module "memorystore" {
  source = "../../modules/memorystore"

  project_id              = var.project_id
  region                  = var.region
  instance_name           = var.redis_instance_name
  tier                    = var.redis_tier
  memory_size_gb          = var.redis_memory_size_gb
  redis_version           = var.redis_version
  authorized_network      = module.network.vpc_id
  auth_enabled            = var.redis_auth_enabled
  transit_encryption_mode = var.redis_transit_encryption_mode

  depends_on = [module.network]
}

module "secrets" {
  source = "../../modules/secrets"

  project_id       = var.project_id
  region           = var.region
  secret_names     = var.secret_names
  runtime_sa_email = module.iam.runtime_sa_email
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id                      = var.project_id
  region                          = var.region
  repository_id                   = var.ar_repo_name
  keep_recent_count               = var.ar_keep_recent_count
  delete_untagged_older_than_days = var.ar_delete_untagged_older_than_days
}

module "cloud_build" {
  source = "../../modules/cloud_build"

  project_id            = var.project_id
  region                = var.cloud_build_region
  trigger_name          = var.cloud_build_trigger_name
  github_owner          = var.github_owner
  github_repo           = var.github_repo
  branch_regex          = var.github_branch_regex
  build_config_filename = var.cloud_build_config_filename
  service_account       = module.iam.cicd_sa_name
  substitutions         = var.cloud_build_substitutions
}

######################################################################
# Shared Cloud Run runtime config.
######################################################################

locals {
  # Initial image used to seed every workload. Cloud Build rewrites the
  # tag per push; ignore_changes on the image attribute prevents drift.
  app_image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.ar_repo_name}/${var.image_name}:${var.image_tag}"

  egress_subnet = module.network.egress_subnet_id
  runtime_sa    = module.iam.runtime_sa_email

  # Connection metadata injected into every workload, merged on top of
  # operator-supplied runtime_env.
  base_env = {
    INSTANCE_CONNECTION_NAME = module.cloud_sql.connection_name
    REDIS_HOST               = module.memorystore.host
    REDIS_PORT               = tostring(module.memorystore.port)
  }

  runtime_env = merge(local.base_env, var.runtime_env)
}

######################################################################
# Cloud Run Job — database migrations.
######################################################################

module "cloud_run_job" {
  source = "../../modules/cloud_run_job"

  project_id       = var.project_id
  region           = var.region
  job_name         = var.migrate_job_name
  image            = local.app_image
  command          = var.migrate_command
  cpu              = var.migrate_cpu
  memory           = var.migrate_memory
  service_account  = local.runtime_sa
  egress_subnet_id = local.egress_subnet
  vpc_egress       = var.vpc_egress
  env              = local.runtime_env
  secret_env       = var.runtime_secret_env
}

######################################################################
# Cloud Run Service — API. Public via the load balancer.
######################################################################

module "cloud_run_api" {
  source = "../../modules/cloud_run_service"

  project_id            = var.project_id
  region                = var.region
  service_name          = var.api_service_name
  image                 = local.app_image
  command               = var.api_command
  cpu                   = var.api_cpu
  memory                = var.api_memory
  cpu_idle              = true
  min_instances         = var.api_min_instances
  max_instances         = var.api_max_instances
  ingress               = var.api_ingress
  allow_unauthenticated = true
  service_account       = local.runtime_sa
  egress_subnet_id      = local.egress_subnet
  vpc_egress            = var.vpc_egress
  port                  = var.container_port
  env                   = local.runtime_env
  secret_env            = var.runtime_secret_env
  startup_probe_path    = var.api_startup_probe_path
  liveness_probe_path   = var.api_liveness_probe_path
}

######################################################################
# Cloud Run Service — Celery worker. Internal only, always-on CPU.
######################################################################

module "cloud_run_worker" {
  source = "../../modules/cloud_run_service"

  project_id            = var.project_id
  region                = var.region
  service_name          = var.worker_service_name
  image                 = local.app_image
  command               = var.worker_command
  cpu                   = var.worker_cpu
  memory                = var.worker_memory
  cpu_idle              = false
  min_instances         = var.worker_min_instances
  max_instances         = var.worker_max_instances
  ingress               = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  allow_unauthenticated = false
  service_account       = local.runtime_sa
  egress_subnet_id      = local.egress_subnet
  vpc_egress            = var.vpc_egress
  port                  = var.container_port
  env                   = local.runtime_env
  secret_env            = var.runtime_secret_env
}

######################################################################
# Cloud Run Service — Celery beat. Internal only, always-on CPU.
######################################################################

module "cloud_run_beat" {
  source = "../../modules/cloud_run_service"

  project_id            = var.project_id
  region                = var.region
  service_name          = var.beat_service_name
  image                 = local.app_image
  command               = var.beat_command
  cpu                   = var.beat_cpu
  memory                = var.beat_memory
  cpu_idle              = false
  min_instances         = var.beat_min_instances
  max_instances         = var.beat_max_instances
  ingress               = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  allow_unauthenticated = false
  service_account       = local.runtime_sa
  egress_subnet_id      = local.egress_subnet
  vpc_egress            = var.vpc_egress
  port                  = var.container_port
  env                   = local.runtime_env
  secret_env            = var.runtime_secret_env
}

######################################################################
# HTTPS LB + Serverless NEG + managed cert for the API domain.
######################################################################

module "lb_serverless_neg" {
  source = "../../modules/lb_serverless_neg"

  project_id             = var.project_id
  region                 = var.region
  name_prefix            = var.lb_name_prefix
  domain                 = var.domain
  cloud_run_service_name = module.cloud_run_api.service_name
  enable_cdn             = var.lb_enable_cdn
}
