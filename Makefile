include .env.dist

USER                       := user
S_USER                     := suser
PASSWORD                   := password
GROUP                      := yoctogroup
POSTGRES_DB                := os-testing-db
OS_IMAGE                   := core-image-minimal
SUSE_VER                   ?= 15.6
METABASE_META_DB_NAME	   := metabase
METABASE_META_USER		   := metabase
METABASE_META_PASS         := metabase

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
METABASE_META_VOLUME	   := ${DOCKER_PREFIX}-metabase-meta-data
METABASE_APP_VOLUME		   := ${DOCKER_PREFIX}-metabase-app

# Paths
HOST_LAYERS_PATH           := ${CURDIR}/layers
HOST_CONF_PATH             := ${CURDIR}/conf
HOST_SCRIPTS_PATH          := ${CURDIR}/scripts
TESTS_DIR                  := ${CURDIR}/tests

# Python
define get_python_required_libs
	python3 -c "import sys; \
		sys.exit(1) if sys.version_info < (3,11) else None;
		import tomllib; from pathlib import Path; \
		print(' '.join(tomllib.loads(Path('pyproject.toml').read_text())['project']['dependencies']))"
endef

PACKAGE_MGR                := uv
PYTHON_REQUIRED_LIBS       := $(shell $(call get_python_required_libs))

# Docker Network
DOCKER_NETWORK             := yocto-network
YOCTO_ADDRESS              := 10.5.0.10
PYTHON_ADDRESS             := 10.5.0.11
SUSE_ADDRESS_156           := 10.5.0.13
BENCHER_API_ADDRESS        := 10.5.0.14
BENCHER_CLI_ADDRESS        := 10.5.0.15
POSTGRES_ADDRESS           := 10.5.0.20
METABASE_ADDRESS		   := 10.5.0.30
METABASE_META_DB_ADDRESS   := 10.5.0.31
SUBNET                     := 10.5.0.0/24
GATEWAY                    := 10.5.0.1
SSH_QEMU_PORT              ?= 2222
SSH_SUSE_PORT_156          := 1616
BENCHER_API_PORT           := 61016
BENCHER_CLI_PORT           := 3000
SSH_POSTGRES_PORT          := 5432
METABASE_PORT			   := 3001

SSH_QEMU_USER              ?= root

# Library
PYTHONDONTWRITEBYTECODE    := 1
PY_LIB_NAME                := $(shell grep -Po 'name\s*=\s*"\K(\w+)' pyproject.toml)

.PHONY: ensure-python-dependencies
ensure-python-dependencies:
	@if [ -z "${PYTHON_REQUIRED_LIBS}" ]; then \
		echo "ERROR: PYTHON_REQUIRED_LIBS is empty."; \
		echo "This might be because you're using Python < 3.11 which doesn't have tomllib module."; \
		echo "Please use Python 3.11 or higher."; \
		echo "You are using $(shell python --version)."; \
		exit 1; \
	fi

.PHONY: docker
docker: ensure-python-dependencies init-submodule
	docker build \
		--tag ${DOCKER_TAG} \
		--build-arg USER="${USER}" \
		--build-arg GROUP="${GROUP}" \
		--build-arg LIB_NAME="${LIB_NAME}" \
		--build-arg PYTHON_REQUIRED_LIBS="${PYTHON_REQUIRED_LIBS}" \
		--build-arg PASSWORD="${PASSWORD}" \
		--build-arg POKY_DIR="${POKY_DIR}" \
		--file docker/image_builder.dockerfile .

.PHONY: docker-init-volumes
docker-init-volumes: ensure-volumes
	docker run -it --rm \
		--env BUILD_DIR=${BUILD_DIR} \
		--env POKY_DIR=${POKY_DIR} \
		--env USER=${USER} \
		--env GROUP=${GROUP} \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_CONF_PATH}/packages.conf:${BUILD_DIR}/conf/packages.conf" \
		--volume "${HOST_LAYERS_PATH}/meta-image-tests:${POKY_DIR}/meta-image-tests" \
		--volume "${HOST_SCRIPTS_PATH}/add-layers.sh:${POKY_DIR}/add-layers.sh" \
		${DOCKER_TAG} \
		bash -c "cd .. && ./add-layers.sh && bitbake ${OS_IMAGE}"

.PHONY: docker-run-image
docker-run-image: docker-init-volumes
	docker run -it --rm \
		--env BUILD_DIR=${BUILD_DIR} \
		--env POKY_DIR=${POKY_DIR} \
		--env USER=${USER} \
		--env GROUP=${GROUP} \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_CONF_PATH}/packages.conf:${BUILD_DIR}/conf/packages.conf" \
		--volume "${HOST_LAYERS_PATH}/meta-image-tests:${POKY_DIR}/meta-image-tests" \
		${DOCKER_TAG} \
		runqemu qemux86-64 slirp nographic

.PHONY: docker-run-metabase
docker-run-metabase: ensure-volumes
	docker compose --file docker/compose.yml --project-directory ./ up --detach imgtests-postgres imgtests-metabase-meta-db imgtests-metabase

.PHONY: docker-compose-up
docker-compose-up: ensure-python-dependencies ensure-volumes
	docker compose --file docker/compose.yml --project-directory ./ up --detach --build

.PHONY: docker-compose-down
docker-compose-down:
	docker compose --file docker/compose.yml --project-directory ./ down

.PHONY: ensure-volumes
ensure-volumes: docker
	@for volume in ${DOCKER_OPENSUSE_VOLUME} ${BENCHER_API_CONF_VOLUME} ${BENCHER_API_DB_VOLUME} ${METABASE_META_VOLUME} ${METABASE_APP_VOLUME}; do \
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
	@echo "  docker-run-metabase				Run Postgres database with Metabase containers"
	@echo -n "  ${PACKAGE_MGR}"
	@echo     "                                 Updates the project's Python environment with the '${PACKAGE_MGR}';"
	@echo "  ensure-volumes                     Creates volumes if missing and changes ownership;"
	@echo "  ensure-python-dependencies         Checks that Python 3.11+ is available and required dependencies can be extracted;"
	@echo "  init-submodule                     Recursive initialization git submodules;"
	@echo "  pre-commit-check                   Check source code with pre-commit hooks;"
	@echo "  unit-test                          Run unit tests for the Python library '${PY_LIB_NAME}';"
	@echo "  help                               Displays information about all available targets."

.EXPORT_ALL_VARIABLES:
