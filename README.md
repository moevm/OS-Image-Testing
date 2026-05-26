# OS-Image-Testing

Performance and Endurance Testing of OS images.

Repository structure:

| Folder            | Description                              |
|-------------------|------------------------------------------|
| [conf](conf)      | Configuration files                      |
| [docker](docker)  | Essential Docker-related files           |
| [docs](docs)      | Markdown documentation of the repository |
| [layers](layers)  | Layers content                           |
| [scripts](scripts)| Shell scripts                            |
| [src](src)        | Source code and core development files   |
| [tests](tests)    | Image and unit tests                     |

## Building and testing Yocto image via Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/moevm/OS-Image-Testing.git

cd OS-Image-Testing
```

For getting information about available commands run:

```bash
make help
```

### 2. Base initialization of Docker volumes and subsequent image building

```bash
make docker-compose-up
```

After initializing both Docker image and volumes, starts the following containers:

- Python container is used for sending test input and receiving test output from the Yocto and Suse containers through SSH. It starts after the building processes are complete and the image has been booted. Communicates with other containers also via SSH.

- Yocto container (port:2222) is used for running tests after building the Yocto image. Building the image requires a significant amount of time and resources.

- Suse-156 container (port:1616) is another system for running tests, that also builds through QEMU.

- Postgres container (port:5432) contains the project database, which includes configurations, experiment results, information about system loaders and observers.

- Bencher-API container (port:61016) is used as a bencher server. It contains the separate database and processes all requests, that can be seen in the container logs.

- Bencher-console container (port:3000) shows active bencher web sessions used for viewing graphics and stats on tested systems, as well as the test results.

Results can be obtained from the Python container logs after all the tests are finished:

```bash
docker logs os-image-testing-imgtests-analyzer-1
```

Note: To create an image with all the packages specified in conf/packages.conf, you will need at least 200 GB of free disk space. If your memory is running low, consider removing unnecessary packages.

To add a new utility, you need to update the [packages.conf](conf/packages.conf), [local.conf](conf/local.conf) and write the appropriate [recipe](layers/meta-image-tests/).

### 3. Enviroment configuration

[.env.dist](.env.dist) is used to store env variables, which is included by Makefile. It describes the parameters:
* Common variables (users, passwords)
* VMs parameters (Yocto and Suse paths, Yocto image)
* QEMU parameters (RAM size)
* Network parameters (IP addresses, ports, including SSH ports for VMs)

```bash
make docker-init-volumes
```

Runs QEMU in an assembled docker image.

```bash
make docker-run-image
```

To add a new utility, you need to update the local.conf and write the appropriate recipe, then add the paths to the recipe and dependent files for all called containers in the `Makefile`.

### 3. View test results with Metabase
#### 3.1 Start Metabase

Runs PosgreSQL containers with tests data, Metabase metadata and Metabase service itself:
```bash
make docker-run-metabase
```

After start, Metabase will be accessable at `localhost:3001`

#### 3.2 Import Metabase dashboard

To view tests results, you need to import Metabase dashboard or make it from scratch.

To import Metabase dashboard from `.dump` file:

- Start all Metabase containers:
```bash
make docker-run-metabase
```

- Stop Metabase container with:
```bash
docker stop os-image-testing-imgtests-metabase-1
```

- Clear Metabase metadata:
```bash
docker exec -i os-image-testing-imgtests-metabase-meta-db-1 psql -U metabase -d postgres -c "DROP DATABASE metabase;"

docker exec -i os-image-testing-imgtests-metabase-meta-db-1 psql -U metabase -d postgres -c "CREATE DATABASE metabase;"
```

- Import data from `.dump` file:
```bash
docker exec -i os-image-testing-imgtests-metabase-meta-db-1 pg_restore -U metabase -d metabase < your_dump_file.dump
```

- Start Metabase:
```bash
docker start os-image-testing-imgtests-metabase-1
```
