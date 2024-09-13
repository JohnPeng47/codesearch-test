#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print error messages
error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# Check if script is run with root privileges
if [ "$EUID" -ne 0 ]; then
    error "Please run this script as root or with sudo."
fi

# Update system
echo "Updating system..."
apt update && apt upgrade -y || error "Failed to update system"

# Install Nginx if not already installed
echo "Installing Nginx..."
apt install nginx -y || error "Failed to install Nginx"

# Install Certbot and Nginx plugin
echo "Installing Certbot and Nginx plugin..."
apt install certbot python3-certbot-nginx -y || error "Failed to install Certbot"

# Prompt for domain name
read -p "Enter your domain name (e.g., example.com): " domain

# Obtain and install certificate
echo "Obtaining and installing SSL certificate for $domain..."
certbot --nginx -d "$domain" --non-interactive --agree-tos --redirect \
    --staple-ocsp --email "webmaster@$domain" || error "Failed to obtain/install certificate"

# Set up auto-renewal
echo "Setting up auto-renewal..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -

echo "Let's Encrypt SSL certificate has been successfully set up for $domain with Nginx!"
echo "Certificate will auto-renew every 60 days."