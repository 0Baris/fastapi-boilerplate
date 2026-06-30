######################################################################
# External HTTPS load balancer fronting a Cloud Run service.
#
# Topology:
#   global_forwarding_rule (443)
#     └── target_https_proxy
#           ├── certificate_map ── certificate_map_entry ── cert (DNS auth)
#           └── url_map
#                 └── backend_service
#                       └── serverless NEG → Cloud Run service
#
# The managed cert uses Certificate Manager DNS authorization. The
# operator publishes the single CNAME emitted by the dns_authorization
# output before the cert transitions to ACTIVE.
######################################################################

######################################################################
# Anycast IPv4 — point the domain's A record at this address.
######################################################################

resource "google_compute_global_address" "lb_ipv4" {
  project    = var.project_id
  name       = "${var.name_prefix}-lb-ipv4"
  ip_version = "IPV4"
}

######################################################################
# Serverless NEG → Cloud Run service.
######################################################################

resource "google_compute_region_network_endpoint_group" "this" {
  project               = var.project_id
  region                = var.region
  name                  = "${var.name_prefix}-neg"
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = var.cloud_run_service_name
  }
}

######################################################################
# Backend service. Request-level logging on for LB→Cloud Run tracing.
######################################################################

resource "google_compute_backend_service" "this" {
  project               = var.project_id
  name                  = "${var.name_prefix}-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  enable_cdn            = var.enable_cdn

  backend {
    group = google_compute_region_network_endpoint_group.this.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

######################################################################
# URL map — single host, single backend.
######################################################################

resource "google_compute_url_map" "this" {
  project         = var.project_id
  name            = "${var.name_prefix}-urlmap"
  default_service = google_compute_backend_service.this.id

  host_rule {
    hosts        = [var.domain]
    path_matcher = "default"
  }

  path_matcher {
    name            = "default"
    default_service = google_compute_backend_service.this.id
  }
}

######################################################################
# Certificate Manager — DNS authorization + managed cert + map entry.
######################################################################

resource "google_certificate_manager_dns_authorization" "this" {
  project = var.project_id
  name    = "${var.name_prefix}-dns-auth"
  domain  = var.domain
}

resource "google_certificate_manager_certificate" "this" {
  project = var.project_id
  name    = "${var.name_prefix}-cert"
  scope   = "DEFAULT"

  managed {
    domains            = [var.domain]
    dns_authorizations = [google_certificate_manager_dns_authorization.this.id]
  }
}

resource "google_certificate_manager_certificate_map" "this" {
  project = var.project_id
  name    = "${var.name_prefix}-cert-map"
}

resource "google_certificate_manager_certificate_map_entry" "this" {
  project      = var.project_id
  name         = "${var.name_prefix}-cert-map-entry"
  map          = google_certificate_manager_certificate_map.this.name
  certificates = [google_certificate_manager_certificate.this.id]
  hostname     = var.domain
}

######################################################################
# HTTPS target proxy + global forwarding rule.
# certificate_map must be in the //certificatemanager... URI form.
######################################################################

resource "google_compute_target_https_proxy" "this" {
  project         = var.project_id
  name            = "${var.name_prefix}-https-proxy"
  url_map         = google_compute_url_map.this.id
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.this.id}"
}

resource "google_compute_global_forwarding_rule" "this" {
  project               = var.project_id
  name                  = "${var.name_prefix}-https-fr"
  target                = google_compute_target_https_proxy.this.id
  port_range            = "443"
  ip_address            = google_compute_global_address.lb_ipv4.address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}
