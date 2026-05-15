terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# --- Networking ----------------------------------------------------------

resource "google_compute_network" "vpc" {
  name                    = "auto-healing-vpc"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "demo_ports" {
  name    = "auto-healing-demo-ports"
  network = google_compute_network.vpc.name

  # SSH from anywhere by convention; demo ports locked down to allowed_cidr.
  source_ranges = ["0.0.0.0/0"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_firewall" "demo_ui_ports" {
  name    = "auto-healing-demo-ui"
  network = google_compute_network.vpc.name

  source_ranges = [var.allowed_cidr]
  allow {
    protocol = "tcp"
    ports    = ["3000", "5000", "9090", "9093"]
  }
}

# --- VM ------------------------------------------------------------------

resource "google_compute_instance" "demo" {
  name         = "auto-healing-demo"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      # Ubuntu 22.04 LTS keeps Docker happy without extra configuration.
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30
    }
  }

  network_interface {
    network = google_compute_network.vpc.name
    access_config {
      # Ephemeral public IP. terraform destroy releases it cleanly.
    }
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${var.ssh_public_key}"
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh", {
    repo_url = var.repo_url
    ssh_user = var.ssh_user
  })

  tags = ["auto-healing"]
}
