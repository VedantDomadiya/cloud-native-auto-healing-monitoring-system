output "vm_public_ip" {
  description = "Ephemeral external IP. Released by terraform destroy."
  value       = google_compute_instance.demo.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  description = "Convenience SSH command using the configured user."
  value       = "ssh ${var.ssh_user}@${google_compute_instance.demo.network_interface[0].access_config[0].nat_ip}"
}

output "grafana_url" {
  description = "Grafana UI once the startup script finishes (admin/admin)."
  value       = "http://${google_compute_instance.demo.network_interface[0].access_config[0].nat_ip}:3000"
}

output "prometheus_url" {
  value = "http://${google_compute_instance.demo.network_interface[0].access_config[0].nat_ip}:9090"
}

output "estimated_hourly_cost_usd" {
  description = "Rough cost reminder. e2-medium is ~$0.034/hr in us-central1 (2026 pricing)."
  value       = "~0.034 (e2-medium) + tiny network egress + 30 GB pd-balanced ~$0.005/hr"
}
