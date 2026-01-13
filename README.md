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
| [tests](tests)    | Image tests                              |

## Building and testing Yocto image via Docker Сompose

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

#### 2.1 Initialization through Docker Compose and SSH

After initializing both Docker image and volumes, starts two containers:

- Yocto container is used for running tests after building the Yocto image. Building the image requires a significant amount of time and resources.

- Python container is used for sending test input and receiving test output from the Yocto container through SSH. It starts after the building processes are complete and the image has been booted.

```bash
make docker-compose-up
```

Results can be obtained from the Python container logs after all the tests are finished:

```bash
docker logs os-image-testing-imgtests-analyzer-1
```

Note: To create an image with all the packages specified in conf/packages.conf, you will need at least 200 GB of free disk space. If your memory is running low, consider removing unnecessary packages.

#### 2.2 Manual initialization through Docker [**DEPRECATED**]

Builds Docker image and initializes the volumes, then starts the process of building the OS image.

```bash
make docker-init-volumes
```

Runs QEMU in an assembled docker image.

```bash
make docker-run-image
```

Runs QEMU tests via ptest-runner.

```bash
make docker-test-image
```

To add a test using, for example, **stress-ng**, go to the layers/meta-image-tests/recipes-tests folder, then to endurance-tests or performance-tests, depending on the type of test, then add the test to the folder of the chosen subsystem and update the corresponding .bb file.

To add a new utility, you need to update the local.conf and write the appropriate recipe, then add the paths to the recipe and dependent files for all called containers in the `Makefile`.
