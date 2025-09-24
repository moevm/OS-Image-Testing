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
		${DOCKER_TAG} \
		bash -c "bitbake-layers add-layer ${LAYER_DIR} && bitbake ${OS_IMAGE}"


.PHONY: docker docker-init-volumes
