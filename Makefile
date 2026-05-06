USER                       := user
S_USER                     := suser
PASSWORD                   := password
GROUP                      := yoctogroup
POSTGRES_DB                := os-testing-db
OS_IMAGE                   := core-image-minimal
SUSE_VER                   ?= 15.6
LIB_NAME                   := imgtests

# Docker
DOCKER_PREFIX              := ${LIB_NAME}
DOCKER_TAG                 := ${DOCKER_PREFIX}-yocto-builder
DOCKER_SUSE_TAG            := ${DOCKER_PREFIX}-open-suse-env
DOCKER_PYTHON_TAG          := ${DOCKER_PREFIX}-analyzer
DOCKER_BUILD_VOLUME        := ${DOCKER_PREFIX}-yocto-build
DOCKER_DOWNLOADS_VOLUME    := ${DOCKER_PREFIX}-yocto-downloads
DOCKER_SSTATE_VOLUME       := ${DOCKER_PREFIX}-yocto-sstate
DOCKER_OPENSUSE_VOLUME     := ${DOCKER_PREFIX}-open-suse-files
DOCKER_POSTGRES_VOLUME	   := ${DOCKER_PREFIX}-postgres-data
BENCHER_API_CONF_VOLUME    := ${DOCKER_PREFIX}-bencher-conf
BENCHER_API_DB_VOLUME      := ${DOCKER_PREFIX}-bencher-database
BENCHER_API_LOGS_VOLUME    := ${DOCKER_PREFIX}-bencher-logs
VMETRICS_DATA_VOLUME	   := ${DOCKER_PREFIX}-vmetrics-data

# VictoriaMetrics-docker-network
DEFAULT_NE_PORT		       := 9100
YOCTO_NE_PORT		   	   := 9100
SUSE_156_NE_PORT		   := 9166

# Paths
POKY_DIR                   := /home/${USER}/poky
SUSE_DIR                   := /home/${USER}/suse
BUILD_DIR                  := ${POKY_DIR}/build
HOST_LAYERS_PATH           := ${CURDIR}/layers
HOST_CONF_PATH             := ${CURDIR}/conf
HOST_SCRIPTS_PATH          := ${CURDIR}/scripts
TESTS_DIR                  := ${CURDIR}/tests

# Python
PACKAGE_MGR                := uv

# Docker Network
DOCKER_NETWORK             := yocto-network
YOCTO_ADDRESS              := 10.5.0.10
PYTHON_ADDRESS             := 10.5.0.11
SUSE_ADDRESS_156           := 10.5.0.13
BENCHER_API_ADDRESS        := 10.5.0.14
BENCHER_CLI_ADDRESS        := 10.5.0.15
POSTGRES_ADDRESS           := 10.5.0.20
VMETRICS_ADDRESS 		   := 10.5.0.25
SUBNET                     := 10.5.0.0/24
GATEWAY                    := 10.5.0.1
SSH_TO_QEMU_PORT		   := 22
SSH_QEMU_PORT              ?= 2222
SSH_SUSE_PORT_156          := 1616
IPERF3_PORT                := 5201
DJANGO_PORT                := 8000
BENCHER_API_PORT           := 61016
BENCHER_CLI_PORT           := 3000
POSTGRES_PORT              := 5432
VMETRICS_PORT              := 8438
DJANGO_SECRET              := $(shell date | sha256sum | tr ' ' '_')

SSH_QEMU_USER              ?= root

# 3Gb of virtual memory for each system
QEMU_VM_RAM				   := 3072

# Library
PYTHONDONTWRITEBYTECODE    := 1
PY_LIB_NAME                := $(shell grep -Po 'name\s*=\s*"\K(\w+)' pyproject.toml)

.PHONY: docker
docker: init-submodule
	docker build \
		--tag ${DOCKER_TAG} \
		--build-arg USER="${USER}" \
		--build-arg GROUP="${GROUP}" \
		--build-arg LIB_NAME="${LIB_NAME}" \
		--build-arg PASSWORD="${PASSWORD}" \
		--build-arg POKY_DIR="${POKY_DIR}" \
		--file docker/image_builder.dockerfile .

.PHONY: docker-compose-up
docker-compose-up: ensure-volumes
	docker compose --file docker/compose.yml --project-directory ./ up --detach --build

.PHONY: docker-compose-down
docker-compose-down:
	docker compose --file docker/compose.yml --project-directory ./ down

.PHONY: ensure-volumes
ensure-volumes: docker
	@for volume in ${DOCKER_OPENSUSE_VOLUME} ${BENCHER_API_CONF_VOLUME} ${BENCHER_API_DB_VOLUME} \
	                ${BENCHER_API_LOGS_VOLUME} ${VMETRICS_DATA_VOLUME} ${DOCKER_POSTGRES_VOLUME}; do \
		if ! docker volume inspect $$volume > /dev/null 2>&1; then \
			docker volume create $$volume; \
		fi \
	done;
	@for volume in ${DOCKER_BUILD_VOLUME} ${DOCKER_DOWNLOADS_VOLUME} ${DOCKER_SSTATE_VOLUME}; do \
		if ! docker volume inspect $$volume > /dev/null 2>&1; then \
			docker volume create $$volume; \
			docker run --rm --user root \
				--entrypoint "" \
				--volume $$volume:/data \
				${DOCKER_TAG} bash -c "chown -R ${USER}:${GROUP} /data"; \
		fi \
	done

.PHONY: init-submodule
init-submodule:
	git submodule update --init --recursive

.PHONY: ${PACKAGE_MGR}
${PACKAGE_MGR}:
	@which ${PACKAGE_MGR} || \
		(echo "Failed to find '${PACKAGE_MGR}'. Required to install '${PACKAGE_MGR}' first." && exit 1)
	@${PACKAGE_MGR} sync

.PHONY: pre-commit-check
pre-commit-check: ${PACKAGE_MGR}
	@uvx pre-commit run --all-files

.PHONY: unit-test
unit-test: ${PACKAGE_MGR}
	@echo "Running tests for the library '${PY_LIB_NAME}''..."
	@COVERAGE_FILE=${TESTS_DIR}/.coverage uv run --with pytest --with pytest-cov pytest ${TESTS_DIR}/unit ${TESTS_DIR}/misc

.PHONY: help
help:
	@echo "Usage:"
	@echo "  make [targets] [arguments]"
	@echo
	@echo "  docker                             Builds a docker image;"
	@echo "  docker-compose-up                  Run tests stand with analysis container and target containers;"
	@echo "  docker-compose-down                Stop all containers;"
	@echo -n "  ${PACKAGE_MGR}"
	@echo     "                                 Updates the project's Python environment with the '${PACKAGE_MGR}';"
	@echo "  ensure-volumes                     Creates volumes if missing and changes ownership;"
	@echo "  init-submodule                     Recursive initialization git submodules;"
	@echo "  pre-commit-check                   Check source code with pre-commit hooks;"
	@echo "  unit-test                          Run unit tests for the Python library '${PY_LIB_NAME}';"
	@echo "  help                               Displays information about all available targets."

.EXPORT_ALL_VARIABLES:
