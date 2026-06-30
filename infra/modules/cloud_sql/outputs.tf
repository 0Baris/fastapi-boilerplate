output "instance_name" {
  description = "The Cloud SQL instance name."
  value       = google_sql_database_instance.this.name
}

output "connection_name" {
  description = "The Cloud SQL connection name (project:region:instance) for the connector / socket path."
  value       = google_sql_database_instance.this.connection_name
}

output "private_ip_address" {
  description = "The private IP address assigned to the instance via PSA."
  value       = google_sql_database_instance.this.private_ip_address
}

output "database_name" {
  description = "The application database name."
  value       = google_sql_database.app.name
}

output "db_user" {
  description = "The application database user name."
  value       = google_sql_user.app.name
}
