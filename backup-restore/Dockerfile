FROM postgres:17

# Install dependencies once (not every run)
RUN apt-get update && apt-get install -y awscli gzip && rm -rf /var/lib/apt/lists/*

# Copy scripts
COPY backup.sh /scripts/backup.sh
COPY restore.sh /scripts/restore.sh

# Make executable
RUN chmod +x /scripts/*.sh