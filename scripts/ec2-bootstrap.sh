#!/usr/bin/env bash
#
# One-shot bootstrap for an Ubuntu 22.04 / 24.04 EC2 instance.
# Installs: Docker, docker-compose plugin, Java 17, Jenkins, git.
#
# Usage:
#   ssh ubuntu@<ec2-host>
#   curl -fsSL <raw-url-of-this-file> -o bootstrap.sh
#   chmod +x bootstrap.sh
#   sudo ./bootstrap.sh
#
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo $0"
  exit 1
fi

echo "==> Updating apt..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release git unzip

# ─── Docker ─────────────────────────────────────────────────────────────────
echo "==> Installing Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

# ─── Java 17 (required by Jenkins) ─────────────────────────────────────────
echo "==> Installing Java 17..."
apt-get install -y fontconfig openjdk-17-jre

# ─── Jenkins ────────────────────────────────────────────────────────────────
echo "==> Installing Jenkins..."
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
  | tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" \
  > /etc/apt/sources.list.d/jenkins.list

apt-get update -y
apt-get install -y jenkins
systemctl enable --now jenkins

# ─── Allow Jenkins to use Docker ───────────────────────────────────────────
usermod -aG docker jenkins
systemctl restart jenkins

echo
echo "==================================================================="
echo " ✅ Bootstrap complete."
echo
echo "  Jenkins URL:  http://$(curl -s ifconfig.me):8080"
echo "  Initial admin password:"
echo "      sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
echo
echo "  Open EC2 Security Group inbound rules:"
echo "    - TCP 8080  (Jenkins UI)"
echo "    - TCP 5000  (Flask app)"
echo "    - TCP 22    (SSH)"
echo "==================================================================="
