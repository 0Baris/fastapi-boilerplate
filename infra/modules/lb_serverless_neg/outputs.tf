output "lb_ip" {
  description = "The anycast IPv4 address of the load balancer. Point the domain's A record here."
  value       = google_compute_global_address.lb_ipv4.address
}

output "dns_authorization_record" {
  description = "The CNAME record the operator must publish for the managed cert to validate (name, type, data)."
  value       = google_certificate_manager_dns_authorization.this.dns_resource_record
}
