######################################################################
# Custom-mode VPC. auto_create_subnetworks is off so we own every
# subnet explicitly.
######################################################################

resource "google_compute_network" "this" {
  name                    = var.vpc_name
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

######################################################################
# Primary regional subnet.
######################################################################

resource "google_compute_subnetwork" "primary" {
  name                     = var.subnet_name
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.this.self_link
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true
}

######################################################################
# Direct VPC Egress subnet. Cloud Run revisions attach a NIC in this
# range (one IP per running instance), so size the CIDR accordingly.
######################################################################

resource "google_compute_subnetwork" "egress" {
  name                     = var.egress_subnet_name
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.this.self_link
  ip_cidr_range            = var.egress_subnet_cidr
  private_ip_google_access = true
}

######################################################################
# Private Service Access (PSA).
# A reserved global address range plus a service networking connection
# give managed services (Cloud SQL, Memorystore) private IPs inside
# this VPC.
######################################################################

resource "google_compute_global_address" "psa" {
  name          = var.psa_range_name
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = var.psa_prefix_length
  network       = google_compute_network.this.id
}

resource "google_service_networking_connection" "psa" {
  network                 = google_compute_network.this.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.psa.name]
}

######################################################################
# Export/import custom routes over the PSA peering so Direct VPC
# Egress traffic can reach the PSA-attached services.
######################################################################

resource "google_compute_network_peering_routes_config" "psa" {
  project              = var.project_id
  peering              = "servicenetworking-googleapis-com"
  network              = google_compute_network.this.name
  import_custom_routes = true
  export_custom_routes = true

  depends_on = [google_service_networking_connection.psa]
}

######################################################################
# Deny-all egress baseline. Highest priority number = lowest
# precedence, so every more-specific allow rule wins over it.
######################################################################

resource "google_compute_firewall" "deny_all_egress" {
  name      = var.deny_all_egress_name
  project   = var.project_id
  network   = google_compute_network.this.name
  direction = "EGRESS"
  priority  = 65000

  destination_ranges = ["0.0.0.0/0"]

  deny {
    protocol = "all"
  }
}

######################################################################
# Allow the runtime SA to reach the PSA range on the DB + Redis ports.
# EGRESS rules filter the source by target_service_accounts (source
# CIDR is not valid on EGRESS), so this only opens egress for the
# workload identity, not the whole network.
######################################################################

resource "google_compute_firewall" "allow_egress_psa" {
  name      = var.allow_egress_psa_name
  project   = var.project_id
  network   = google_compute_network.this.name
  direction = "EGRESS"
  priority  = 1000

  destination_ranges      = ["${google_compute_global_address.psa.address}/${var.psa_prefix_length}"]
  target_service_accounts = [var.runtime_sa_email]

  allow {
    protocol = "tcp"
    ports    = [tostring(var.db_port), tostring(var.redis_port)]
  }
}
