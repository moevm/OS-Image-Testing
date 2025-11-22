USER                       := user
GROUP                      := yoctogroup
OS_IMAGE                   := core-image-minimal
SUSE_VER                   ?= 15.6

# Docker
DOCKER_TAG                 := yocto-builder-image
DOCKER_SUSE_TAG            := open-suse-image-env
DOCKER_BUILD_VOLUME        := yocto-build
DOCKER_DOWNLOADS_VOLUME    := yocto-downloads
DOCKER_SSTATE_VOLUME       := yocto-sstate
DOCKER_OPENSUSE_VOLUME     := open-suse-files

# Paths
POKY_DIR                   := /home/${USER}/poky
SUSE_DIR                   := /home/${USER}/suse
BUILD_DIR                  := ${POKY_DIR}/build
HOST_LAYERS_PATH           := ${CURDIR}/layers
HOST_CONF_PATH             := ${CURDIR}/conf
HOST_SCRIPTS_PATH          := ${CURDIR}/scripts
HOST_TEMP_PATH             := ${CURDIR}/results

# Python
PACKAGE_MGR                := uv
PYTHONDONTWRITEBYTECODE    := 1
PY_LIB_NAME                := $(shell grep -Po 'name\s*=\s*"\K(\w+)' pyproject.toml)

.PHONY: docker
docker:
	docker build \
		--tag ${DOCKER_TAG} \
		--build-arg USER="${USER}" \
		--build-arg GROUP="${GROUP}" \
		--file docker/image_builder.dockerfile .
	docker volume create ${DOCKER_BUILD_VOLUME}
	docker volume create ${DOCKER_DOWNLOADS_VOLUME}
	docker volume create ${DOCKER_SSTATE_VOLUME}
	docker run --rm --user root \
		--entrypoint "" \
		--volume ${DOCKER_BUILD_VOLUME}:/tmp-build \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:/tmp-downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:/tmp-sstate \
		${DOCKER_TAG} \
		bash -c "mkdir -p /tmp-build/build /tmp-build/conf && \
			mkdir -p /tmp-downloads && \
			mkdir -p /tmp-sstate && \
			chown -R ${USER}:${GROUP} /tmp-build /tmp-downloads /tmp-sstate"

.PHONY: docker-init-volumes
docker-init-volumes:
	git submodule update --init --recursive
	docker run -it --rm \
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
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_CONF_PATH}/packages.conf:${BUILD_DIR}/conf/packages.conf" \
		--volume "${HOST_LAYERS_PATH}/meta-image-tests:${POKY_DIR}/meta-image-tests" \
		${DOCKER_TAG} \
		runqemu qemux86-64 slirp nographic

.PHONY: docker-test-image
docker-test-image: docker-init-volumes
	@echo "Starting QEMU test..."
	@mkdir -p ${HOST_TEMP_PATH}; \
	chmod 757 "${HOST_TEMP_PATH}"; \
	CONTAINER_ID=$$(docker run -d --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_CONF_PATH}/packages.conf:${BUILD_DIR}/conf/packages.conf" \
		--volume "${HOST_LAYERS_PATH}/meta-image-tests:${POKY_DIR}/meta-image-tests" \
		--volume "${HOST_TEMP_PATH}:/tmp/results" \
		--volume "${HOST_SCRIPTS_PATH}:/tmp/scripts" \
		${DOCKER_TAG} \
		bash /tmp/scripts/run-qemu-test.sh); \
	{ \
		echo "Waiting for container $$CONTAINER_ID..."; \
		docker wait "$$CONTAINER_ID"; \
		docker logs "$$CONTAINER_ID" > "${HOST_TEMP_PATH}/container.log" 2>&1; \
		echo "=== SCREEN LOG ==="; \
		cat "${HOST_TEMP_PATH}/screen.log" 2>/dev/null || echo "Screen log not found"; \
		rm -rf "${HOST_TEMP_PATH}"; \
		echo "QEMU test completed. Press enter"; \
	} &
	@echo "QEMU test started in background"

.PHONY: docker-suse
docker-suse:
	docker build \
		--tag ${DOCKER_SUSE_TAG} \
		--build-arg USER="${USER}" \
		--file docker/open-suse.dockerfile .
	docker volume create ${DOCKER_OPENSUSE_VOLUME}

.PHONY: docker-init-suse
docker-init-suse:
	docker run -it --rm \
		--volume ${DOCKER_OPENSUSE_VOLUME}:${SUSE_DIR} \
		--volume "${HOST_SCRIPTS_PATH}/download-opensuse-images.sh:${SUSE_DIR}/download-opensuse-images.sh" \
		${DOCKER_SUSE_TAG} \
		bash -c "./download-opensuse-images.sh ${SUSE_VER}"

.PHONY: docker-run-suse
docker-run-suse:
	docker run -it --rm \
		--volume ${DOCKER_OPENSUSE_VOLUME}:${SUSE_DIR} \
		${DOCKER_SUSE_TAG} \
		bash -c "qemu-system-x86_64 open-suse-${SUSE_VER}.qcow2 -m 4G -nographic"

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
	@uv run --with pytest pytest

.PHONY: help
help:
	@echo "Usage:"
	@echo "  make [targets] [arguments]"
	@echo
	@echo "  docker                             Builds a docker image;"
	@echo "  docker-suse                        Builds a docker image for openSUSE images environment;"
	@echo "  docker-init-volumes                Initializes docker volumes;"
	@echo "  docker-init-suse                   Downloads openSUSE image (Default: ${SUSE_VER});"
	@echo "      SUSE_VER=[15.5|15.6]"
	@echo "  docker-run-image                   Runs builded Yocto image from builded docker image;"
	@echo "  docker-run-suse                    Runs openSUSE image via QEMU (Default: ${SUSE_VER});"
	@echo "      SUSE_VER=[15.5|15.6]"
	@echo "  docker-test-image                  Tests builded Yocto image from builded docker image;"
	@echo "  pre-commit-check                   Check source code with pre-commit hooks;"
	@echo "  unit-test                          Run unit tests for the Python library '${PY_LIB_NAME}';"
	@echo "  help                               Displays information about all available targets."

.EXPORT_ALL_VARIABLES:
