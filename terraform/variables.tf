variable "project_id" {
  description = "GCP project to provision into."
  type        = string
}

variable "region" {
  description = "GCP region (e.g. us-central1)."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone within the region."
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Compute Engine machine type."
  type        = string
  default     = "e2-medium"
}

variable "allowed_cidr" {
  description = "CIDR allowed to reach the demo ports (e.g. \"203.0.113.5/32\")."
  type        = string
}

variable "repo_url" {
  description = "Git URL the VM clones the project from on first boot."
  type        = string
  default     = "https://github.com/VedantDomadiya/cloud-native-auto-healing-monitoring-system.git"
}

variable "ssh_user" {
  description = "Linux user the SSH key is installed for."
  type        = string
  default     = "demo"
}

variable "ssh_public_key" {
  description = "OpenSSH-formatted public key (e.g. contents of ~/.ssh/id_ed25519.pub)."
  type        = string
}
