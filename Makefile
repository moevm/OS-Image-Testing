USER                       := user
GROUP                      := yoctogroup
OS_IMAGE                   := core-image-minimal
TEST_LAYER                 := meta-image-tests

# Docker
DOCKER_TAG                 := yocto-builder-image
DOCKER_BUILD_VOLUME        := yocto-build
DOCKER_DOWNLOADS_VOLUME    := yocto-downloads
DOCKER_SSTATE_VOLUME       := yocto-sstate
DOCKER_TESTS_VOLUME        := yocto-${TEST_LAYER}

# Paths
POKY_DIR                   := /home/${USER}/poky
BUILD_DIR                  := ${POKY_DIR}/build
LAYER_DIR                  := ${POKY_DIR}/${TEST_LAYER}
HOST_LAYERS_PATH           := ${CURDIR}/layers
HOST_CONF_PATH             := ${CURDIR}/conf


docker:
	docker build \
		--tag ${DOCKER_TAG} \
		--build-arg USER="${USER}" \
		--build-arg GROUP="${GROUP}" \
		--file docker/image_builder.dockerfile .
	docker volume create ${DOCKER_BUILD_VOLUME}
	docker volume create ${DOCKER_DOWNLOADS_VOLUME}
	docker volume create ${DOCKER_SSTATE_VOLUME}
	docker volume create ${DOCKER_TESTS_VOLUME}
	docker run --rm --user root \
		--entrypoint "" \
		--volume ${DOCKER_BUILD_VOLUME}:/tmp-build \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:/tmp-downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:/tmp-sstate \
		--volume ${DOCKER_TESTS_VOLUME}:/tmp-${TEST_LAYER} \
		${DOCKER_TAG} \
		bash -c "mkdir -p /tmp-build/build /tmp-build/conf && \
			mkdir -p /tmp-downloads && \
			mkdir -p /tmp-sstate && \
			mkdir -p /tmp-${TEST_LAYER}/conf && \
			chown -R ${USER}:${GROUP} /tmp-build /tmp-downloads /tmp-sstate /tmp-${TEST_LAYER}"

docker-init-volumes:
	docker run -it --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume ${DOCKER_TESTS_VOLUME}:${LAYER_DIR} \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-login/auto-login/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/auto-login/auto-login_1.0.0.bb" \
		${DOCKER_TAG} \
		bash -c "bitbake-layers add-layer ${LAYER_DIR} && bitbake ${OS_IMAGE}"

docker-run-image: docker-init-volumes
	docker run -it --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume ${DOCKER_TESTS_VOLUME}:${LAYER_DIR} \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-login/auto-login/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/auto-login/auto-login_1.0.0.bb" \
		${DOCKER_TAG} \
		runqemu qemux86-64 slirp nographic

docker-test-image: docker-init-volumes
	@echo "Starting QEMU test..."
	@TEMP_DIR=$$(mktemp -d); \
	chmod 777 "$$TEMP_DIR"; \
	LOG_FILE="$$TEMP_DIR/test.log"; \
	CONTAINER_ID=$$(docker run -d --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume ${DOCKER_TESTS_VOLUME}:${LAYER_DIR} \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-login/auto-login/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/auto-login/auto-login_1.0.0.bb" \
		--volume "$$TEMP_DIR:/tmp/results" \
		${DOCKER_TAG} \
		bash -c "\
			screen -L -Logfile /tmp/results/screen.log -h 10000 -dmS qemu runqemu qemux86-64 slirp nographic; \
			timeout 120 bash -c 'while ! grep -q \"login:\" /tmp/results/screen.log 2>/dev/null; do sleep 5; echo \"Waiting...\"; done'; \
			if [ $$? -eq 0 ]; then \
				> /tmp/results/screen.log; \
				echo 'Running stress-ng tests...'; \
				screen -S qemu -X stuff 'ptest-runner stress-ng\n'; \
				timeout 600 bash -c 'while ! grep -q \"STOP: ptest-runner\" /tmp/results/screen.log 2>/dev/null; do sleep 5; echo \"Tests running...\"; done'; \
				echo 'Shutting down QEMU...'; \
				screen -S qemu -X stuff 'poweroff\n'; \
				sleep 10; \
			else \
				echo 'QEMU boot timeout'; \
			fi; \
			echo 'Container execution completed'"); \
	{ \
		echo "Waiting for container $$CONTAINER_ID..."; \
		docker wait "$$CONTAINER_ID"; \
		docker logs "$$CONTAINER_ID" > "$$TEMP_DIR/container.log" 2>&1; \
		echo "=== SCREEN LOG ==="; \
		cat "$$TEMP_DIR/screen.log" 2>/dev/null || echo "Screen log not found"; \
		rm -rf "$$TEMP_DIR"; \
		echo "QEMU test completed. Press enter"; \
	} &
	@echo "QEMU test started in background"

help:
	@echo "Usage:"
	@echo "  make [targets] [arguments]"
	@echo
	@echo "  docker                 Builds a docker image;"
	@echo "  docker-init-volumes    Initializes docker volumes;"
	@echo "  docker-run-image       Runs builded Yocto image from builded docker image;"
	@echo "  docker-test-image      Tests builded Yocto image from builded docker image;"
	@echo "  help                   Displays information about all available targets."


.PHONY: docker docker-init-volumes run-image test-image
