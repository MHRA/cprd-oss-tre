#!/bin/bash
set -o pipefail
set -o nounset
# set -o xtrace

counter=0
exec_number=5

echo 'Pulling Sonatype Nexus image...'
while  ! docker pull sonatype/nexus3; do
  # We are going to try up to exec_number times.
  if [ $counter -gt $exec_number ]; then
    echo 'ERROR - It was not possible to pull Sonatype Nexus image.'
    exit 1
  fi

  # Restart Docker daemon and try once more.
  systemctl restart docker.service
  sleep 5
  ((counter++))
done

# Run Sonatype Nexus container.
docker run -d -p 80:8081 -p 443:8443 -p 8083:8083 -v /etc/nexus-data:/nexus-data \
  --restart always \
  --name nexus \
  --log-driver local \
  sonatype/nexus3
