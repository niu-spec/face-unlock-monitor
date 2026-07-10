#!/usr/bin/env bash
# Install Jenkins on Ubuntu/Debian cloud server (one-time setup).
# Usage: sudo bash deploy/install_jenkins.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo bash deploy/install_jenkins.sh" >&2
  exit 1
fi

echo "[jenkins] installing Java + Jenkins..."

apt-get update
apt-get install -y openjdk-17-jre fontconfig curl

if [ ! -f /usr/share/keyrings/jenkins-keyring.asc ]; then
  curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
    | tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
fi

if [ ! -f /etc/apt/sources.list.d/jenkins.list ]; then
  echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
    > /etc/apt/sources.list.d/jenkins.list
fi

apt-get update
apt-get install -y jenkins

systemctl enable jenkins
systemctl start jenkins

# Allow Jenkins to use Docker (MediaMTX restart during deploy).
if getent group docker >/dev/null 2>&1; then
  usermod -aG docker jenkins || true
fi

echo ""
echo "[jenkins] installed successfully."
echo "[jenkins] initial admin password:"
cat /var/lib/jenkins/secrets/initialAdminPassword
echo ""
echo "[jenkins] open http://$(hostname -I | awk '{print $1}'):8080"
echo "[jenkins] next steps: docs/B组-Jenkins安装指引.md"
