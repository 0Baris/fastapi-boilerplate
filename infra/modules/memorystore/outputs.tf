output "instance_name" {
  description = "The Memorystore instance name."
  value       = google_redis_instance.this.name
}

output "host" {
  description = "The private IP/host of the Redis instance."
  value       = google_redis_instance.this.host
}

output "port" {
  description = "The port the Redis instance is reachable on."
  value       = google_redis_instance.this.port
}

output "auth_string" {
  description = "The AUTH string for the instance (null when auth disabled)."
  value       = google_redis_instance.this.auth_string
  sensitive   = true
}
