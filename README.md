# OS-Image-Testing

Performance and Endurance Testing of OS images

Repository structure:

| Folder            |Description                               |
|-------------------|------------------------------------------|
| [docker](docker)  | Essential Docker-related files           |
| [docs](docs)      | Markdown documentation of the repository |
| [layers](layers)  | Layers content                           |
| [src](src)        | Source code and core development files   |
| [tests](tests)    | Image tests                              |

## Building Yocto testing image via Docker

### 1. Clone the repository and getting help

```bash
git clone https://github.com/moevm/OS-Image-Testing.git

cd OS-Image-Testing
```

For getting information about available commands run `make help`.

### 2. Base initialization docker volumes and subsequent building image

```
# Building docker image and initialization volumes for building and running OS into them
make docker

# Starting the OS image build
make docker-init-volumes

# Running QEMU in an assembled docker image
make docker-run-image

# Running QEMU testing via ptest-runner
make docker-test-image
```

To add a test using, for example, **stress-ng**, go to the layers/meta-image/tests/recipes-tests folder, then to endurance-tests or performance-tests, depending on the type of test, then add the test to the folder of the chosen subsystem and update the corresponding .bb file.

To add a new utility, you need to update the local.conf and write the appropriate recipe, then add the paths to the recipe and dependent files for all called containers in the `Makefile`.

## OpenSUSE testing

```
# Building docker image for building and running openSUSE into them
make docker-suse

# Starting downloads necessary openSUSE images
make docker-init-suse [SUSE_VER=[15.5|15.6]]

# Running openSUSE in the docker container via QEMU
make docker-run-suse [SUSE_VER=[15.5|15.6]]
```
