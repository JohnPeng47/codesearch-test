#!/bin/sh

# Function to display usage
usage() {
    echo "Usage: $0 <dbname> <password> [username]"
    echo "  dbname: Name of the database to create (required)"
    echo "  password: Password for the user (required)"
    echo "  username: Name of the user to create (optional, defaults to 'postgres')"
    exit 1
}

# Check if required arguments are provided
if [ $# -lt 2 ]; then
    echo "Error: Insufficient arguments"
    usage
fi

DB_NAME="$1"
DB_PASS="$2"
DB_USER=${3:-postgres}

echo "Starting PostgreSQL setup script..."
echo "Database Name: $DB_NAME"
echo "Username: $DB_USER"
echo "Password: [hidden for security]"

echo "Updating package list and installing PostgreSQL..."
sudo apt update
sudo apt install -y postgresql postgresql-contrib

echo "Starting PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

echo "Setting up PostgreSQL..."
if [ "$DB_USER" != "postgres" ]; then
    echo "Creating new user: $DB_USER"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
else
    echo "Updating password for existing postgres user"
    sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '$DB_PASS';"
fi

echo "Creating database: $DB_NAME"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"

echo "Granting privileges on $DB_NAME to $DB_USER"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "Configuring PostgreSQL to listen on 127.0.0.1..."
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '127.0.0.1'/" /etc/postgresql/*/main/postgresql.conf

echo "Updating pg_hba.conf to allow password authentication for local connections..."
echo "host    $DB_NAME    $DB_USER    127.0.0.1/32    md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf

echo "Restarting PostgreSQL to apply changes..."
sudo systemctl restart postgresql

echo "PostgreSQL setup completed successfully!"
echo "You can now connect using the following SQLAlchemy URI:"
echo "SQLALCHEMY_DATABASE_URI = \"postgresql://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME\""