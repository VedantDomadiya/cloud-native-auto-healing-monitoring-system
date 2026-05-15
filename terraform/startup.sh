#!/bin/bash
# Startup script executed on first boot of the GCE instance.
# Installs Docker + Compose + Minikube + kubectl + Python and clones the repo.
#
# LF line endings are required (Terraform reads this verbatim and passes it
# to GCE, which executes it on Linux). On Windows, ensure your editor saves
# this with LF; git autocrlf=input keeps the LF when committed.
set -euxo pipefail

REPO_URL="${repo_url}"
SSH_USER="${ssh_user}"

# --- System packages -----------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
    ca-certificates curl gnupg lsb-release \
    git make python3.11 python3.11-venv python3-pip \
    conntrack

# --- Docker --------------------------------------------------------------
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker
usermod -aG docker "${SSH_USER}" || true

# --- kubectl -------------------------------------------------------------
KCV=$(curl -sL https://dl.k8s.io/release/stable.txt)
curl -L "https://dl.k8s.io/release/$KCV/bin/linux/amd64/kubectl" -o /usr/local/bin/kubectl
chmod +x /usr/local/bin/kubectl

# --- Minikube ------------------------------------------------------------
curl -L "https://storage.googleapis.com/minikube/releases/v1.33.1/minikube-linux-amd64" -o /usr/local/bin/minikube
chmod +x /usr/local/bin/minikube

# --- Clone the project as the demo user ----------------------------------
sudo -u "${SSH_USER}" git clone "${REPO_URL}" "/home/${SSH_USER}/auto-healing-system" || true

cat > "/home/${SSH_USER}/README-vm.txt" <<EOF
The auto-healing project is checked out at:
    /home/${SSH_USER}/auto-healing-system

Bring the stack up with:
    cd /home/${SSH_USER}/auto-healing-system
    make up

Grafana       http://$(curl -sH 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip):3000
Prometheus    http://$(curl -sH 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip):9090
EOF
chown "${SSH_USER}:${SSH_USER}" "/home/${SSH_USER}/README-vm.txt"

echo "Startup complete."
