output "vpc_id" {
  description = "The VPC network ID."
  value       = google_compute_network.this.id
}

output "vpc_self_link" {
  description = "The VPC network self link (used by Cloud SQL private_network)."
  value       = google_compute_network.this.self_link
}

output "vpc_name" {
  description = "The VPC network name."
  value       = google_compute_network.this.name
}

output "primary_subnet_id" {
  description = "The primary subnet ID (projects/.../subnetworks/<name> form)."
  value       = google_compute_subnetwork.primary.id
}

output "egress_subnet_id" {
  description = "The Direct VPC Egress subnet ID (projects/.../subnetworks/<name> form)."
  value       = google_compute_subnetwork.egress.id
}

output "psa_connection" {
  description = "The service networking connection enabling PSA private IPs."
  value       = google_service_networking_connection.psa.id
}
