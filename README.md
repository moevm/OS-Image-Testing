# OS-Image-Testing

**English** | [Русский](docs/i18n/README_ru.md) |

Performance and Endurance Testing of OS images.

Repository structure:

| Folder                                      | Description                                |
|---------------------------------------------|--------------------------------------------|
| [conf](conf)                                | Configuration files                        |
| [docker](docker)                            | Essential Docker-related files             |
| [docs](docs)                                | Markdown documentation of the repository   |
| [layers](layers)                            | Layers content (for Poky)                  |
| [metabase_prototype](metabase_prototype)    | Metabase files: queries and synthetic data |
| [scripts](scripts)                          | Shell scripts                              |
| [src](src)                                  | Source code and core development files     |
| [tests](tests)                              | Unit tests and other                       |

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

- Python container (analyzer) is used for sending test input and receiving test output from the Yocto and Suse containers through SSH. It starts after the building processes are complete and the image has been booted.

- Yocto container (port:SSH_QEMU_PORT) is used for running tests after building the Yocto image. Building the image requires a significant amount of time and resources.

- Suse-156 container (port:SSH_SUSE_PORT_156) is another system for running tests, that also builds through QEMU.

- Postgres container (port:POSTGRES_PORT) contains the project database, which includes configurations, experiment results, information about system loaders and observers.

- Bencher-API container (port:BENCHER_API_PORT) is used as a bencher server. It contains the separate database and processes all requests, that can be seen in the container logs.

- Bencher-console container (port:BENCHER_CLI_PORT) shows active bencher web sessions used for viewing graphics and stats on tested systems, as well as the test results.

- Victoria Metrics container (port:VMETRICS_PORT) collects metrics from the Yocto and Suse-156 container provided by node exporters.

- Metabase container: (port:METABASE_PORT) used to create queries and dashboards with collected metrics

- Metabase meta data container: (port:METABASE_META_DB_PORT) needed by Metabase to save settings: queries, dashboards, connection information

Results can be obtained from the Python container logs after all the tests are finished:

```bash
docker logs os-image-testing-imgtests-analyzer-1
```

Note: To create an image with all the packages specified in [packages.conf](conf/packages.conf), you will need at least 200 GB of free disk space. If your memory is running low, consider removing unnecessary packages.

To add a new utility, you need to update the [packages.conf](conf/packages.conf), [local.conf](conf/local.conf) and write the appropriate [recipe](layers/meta-image-tests/).

### 3. Environment configuration

[.env.dist](.env.dist) is used to store env variables, which is included by Makefile. It describes the parameters:
* Common variables (users, passwords)
* VMs parameters (Yocto and Suse paths, Yocto image)
* QEMU parameters (RAM size)
* Network parameters (IP addresses, ports, including SSH ports for VMs)

### 4. View test results with Metabase
#### 4.1 Import Metabase dashboard

To view test results, you need to import Metabase dashboard or make it from scratch.

To import Metabase dashboard from `.dump` file:

- Start all containers:
```bash
make docker-compose up
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

#### 4.2 Start Metabase demonstration

Use metabase to check dashboards examples on a synthetic data

Move to metabase directory and launch metabase via docker compose
```bash
cd metabase_prototype

docker compose up -d
```

Environment configuration for metabase demo can be viewed and configured at `metabase_prototype/.env`
