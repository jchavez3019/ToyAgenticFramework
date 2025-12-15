

Running MongoDB Docker container:
```shell
docker run --name mongo-local -d -p 27017:27017 -e 'MONGO_INITDB_ROOT_USERNAME=admin' -e 'MONGO_INITDB_ROOT_PASSWORD=password' mongo:latest
```

To connect to the database and visualize the data, first install [MongoDB Compass](https://www.mongodb.com/try/download/terraform-provider). 

To set up Redis, use the following Docker command:
```shell
docker run --name redis-broker -d -p 6379:6379 redis
```

We have various Docker containers serving different purposes. Docker Compose is used to set everything up. To run the
dev environment, use the command:
To run the dev environment, use the command:
```shell
docker compose -f docker-compose.base.yml -f docker-compose.[dev/prod].yml --env-file secrets/[dev/prod].env up --build -d
```

The `--build` flag is to build all the containers. `--no-cache` is to ensure we build them from scratch (e.g. when 
there are code changes). The `-d` flag is to ensure all the containers are run in the 'detached' mode. 

In the second command, the `docker-compose.prod.yml` file is used to overwrite changes into the 
`docker-compose.dev.yml` file which is used as a base configuration. The main change that is done is removing the local 
MongoDB container and instead using the URI for the one hosted in MongoDB Atlas. 

To clean up the all services/containers, for the dev/prod configuration, run:
```shell
docker compose -f docker-compose.base.yml -f docker-compose.[dev/prod].yml down
```

To view the currently running containers: 
```shell
docker ps
```
We can also stop a running container:
```shell
docker stop [container_name or ID]
```
We can also delete the container's image:
```shell
docker rm [container_name or ID]
```
Preferably, we should not be singling out containers in this fashion and instead be working with Docker Compose.

To view the logs of all the containers in dev/prod:
```shell
docker compose -f docker-compose.base.yml -f docker-compose.[dev/prod].yml logs -f
```

To connect to the EC2 instance, use SSH:
```shell
ssh -i [your-key-pair-filename].pem ec2-user@[Public IPv4 Address]
```
For the key, it is also recommended to set its permissions using:
```shell
chmod 400 [your-key-pair-filename].pem
```
This ensures the file has read-only access to the user who created the file, and is not visible to any other users.