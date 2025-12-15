# Install Docker
sudo yum update -y
# Start the Docker service
sudo yum install docker -y
sudo systemctl start docker
# Enables Docker to automatically start when the instance boots
sudo systemctl enable docker
# By default, only `root` can run Docker commands. Add `ec2-user` to the group so that we don't need sudo.
# Add the current user to the docker group
sudo usermod -aG docker ${USER}
# Install Docker Compose
# 1) Get the latest version of the `docker-compose` binary from GitHub.
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m) -o /usr/libexec/docker/cli-plugins/docker-compose
# 2) Update the permissions to allow the command to execut.
sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose
# 3) Verify that `docker-compose` has been successfully installed.
docker compose version
# Unfortunately, AWS Linux 2 is very annoying with Docker and installs an old version of buildx. To correct this, we can
# install a new version:
# Let's download a newer version since Docker Compose requires buildx>=0.14.0
BUILDX_VERSION="v0.30.1"
# Set the destination path
BUILDX_PLUGIN_PATH="/usr/libexec/docker/cli-plugins/docker-buildx"
# The exact filename suffix assuming a system running on an Intel/AMD (x86_64) chip. The system will always be Linux
# based (implied in the name AWS Linux 2).
FILENAME_SUFFIX="linux-amd64"
# Download the correct filename
sudo curl -SL https://github.com/docker/buildx/releases/download/$BUILDX_VERSION/buildx-$BUILDX_VERSION.$FILENAME_SUFFIX -o $BUILDX_PLUGIN_PATH
# Give it executable permissions
sudo chmod +x $BUILDX_PLUGIN_PATH
# Verify that docker buildx was installed with the correct version
docker buildx version
# Now, pull this project into the instance
git clone https://github.com/jchavez3019/ToyAgenticFramework.git
cd ToyAgenticFramework/
# NOTE: Don't forget to copy over the `secrets` to the EC2 instance. This MUST be done from a local device, not the
# EC2 instance. To do so, run the following command on local:
# scp -i [your-key-pair-filename].pem -r ./secrets/ ec2-user@[public IPv4 address]:~/ToyAgenticFramework
# You may now optionally spin up the project using Docker Compose:
# DEV spin up
# docker compose -f docker-compose.base.yml -f docker-compose.dev.yml --env-file secrets/dev.env up --build -d
# PROD spin up
# docker compose -f docker-compose.base.yml -f docker-compose.prod.yml --env-file secrets/prod.env up --build -d
# You may also display the logs of the all the containers using:
# docker compose -f docker-compose.base.yml -f docker-compose.[dev/prod].yml logs -f