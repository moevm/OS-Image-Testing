# OS-Image-Testing

**English** | [Русский](docs/i18n/README_ru.md) |

Performance and Endurance Testing of OS images.


## Documentation

[Building images, running tests, and viewing results](docs/guides/testing-guide.md).

### Repository structure

| Folder            | Description                              |
|-------------------|------------------------------------------|
| [conf](conf)      | Configuration files                      |
| [docker](docker)  | Essential Docker-related files           |
| [docs](docs)      | Markdown documentation of the repository |
| [layers](layers)  | Layers content (for Poky)                |
| [scripts](scripts)| Shell scripts                            |
| [src](src)        | Source code and core development files   |
| [tests](tests)    | Unit tests and other                     |

### Methodologies

- [Chaos Engineering](docs/methodology/ChaosEngineering.md)
- [Performance testing](docs/methodology/performance-methodology.md)
- [Comparison matrix](docs/methodology/matrix.md)
- [Tool-based method](docs/methodology/instrumental-method.md)
- [USE method](docs/methodology/use-method.md)
- [Determining memory consumption characteristics](docs/methodology/memory-consumption-characteristics.md)
- [Working set size estimation method](docs/methodology/working-set-size-estimation-method.md)
- [Performance monitoring](docs/methodology/perfomance-monitoring.md)
- [Leak detection method](docs/methodology/leak-detection-method.md)
- [Static performance tuning](docs/methodology/static-performance-tuning.md)
- [Resource management](docs/methodology/resource-management.md)
- [Microbenchmarking](docs/methodology/microbenchmarking.md)
- [Cycle analysis](docs/methodology/cycle-analysis.md)
- [Failure emulation](docs/methodology/failure_emulation.md)

## Building and testing Yocto and Suse image via Docker Compose

### 0. Required dependencies

Before proceeding, make sure you have the following tools installed on your system:
- Git — required to clone the project repository and manage version control;
- GNU Make — required to run build and test commands via make;
- Docker — needed to run the build environment in containers;
- Docker Compose — used to orchestrate multi‑containers;
- Python 3.11+ — required for running auxiliary scripts and tools included in the project.

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

- Victoria Metrics container (port:VMETRICS_PORT) collects metrics from the Yocto and Suse-156 container provided by node exporters.

Results can be obtained from the Python container logs after all the tests are finished:

```bash
docker logs os-image-testing-imgtests-analyzer-1
```

Note: To create an image with all the packages specified in [packages.conf](conf/packages.conf), you will need at least 200 GB of free disk space. If your memory is running low, consider removing unnecessary packages.

To add a new utility, you need to update the [packages.conf](conf/packages.conf), [local.conf](conf/local.conf) and write the appropriate [recipe](layers/meta-image-tests/).

### 3. Enviroment configuration

[.env.dist](.env.dist) is used to store env variables, which is included by Makefile. It describes the parameters:
* Common variables (users, passwords)
* VMs parameters (Yocto and Suse paths, Yocto image)
* QEMU parameters (RAM size)
* Network parameters (IP addresses, ports, including SSH ports for VMs)

## Complete documentation

All project documentation is available in the [docs/index.md](docs/index.md).
