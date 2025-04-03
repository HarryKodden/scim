IMAGE="scim-sample"
REPOSITORY_URL="harrykodden"
#ARCHITECTURE="linux/arm64"
ARCHITECTURE="linux/amd64"
TAG="latest"

all:
	docker build \
	--platform "${ARCHITECTURE}" \
	. \
	-t ${IMAGE} \
	-t ${IMAGE}:${TAG} \
	-t ${REPOSITORY_URL}/${IMAGE}:${TAG}

develop: all
	#docker run -d --name mongo -e MONGO_INITDB_ROOT_USERNAME=mongo -e MONGO_INITDB_ROOT_PASSWORD=secret  amd64/mongo
	#docker run -d --name mysql -e MYSQL_ROOT_PASSWORD=secret mysql:latest
	#docker run --rm --link mongo:mongo --link mysql:mysql -p 8000:80 -ti -v $$PWD/code:/code -v $$PWD/test:/test --entrypoint /usr/local/bin/uvicorn ${IMAGE} main:app --reload --host 0.0.0.0 --port 80
	#docker run --rm -p 8000:80 -ti -v $$PWD/code:/code \
	#	-e JUMPCLOUD_URL=https://console.jumpcloud.com \
	#	-e JUMPCLOUD_KEY=${JUMPCLOUD_KEY} \
	#	--entrypoint /usr/local/bin/uvicorn ${IMAGE} main:app --reload --host 0.0.0.0 --port 80
	# docker \
	#	run --rm \
	#	--network host \
	#	-v $$PWD:/app \
	#	-e LDAP_HOSTNAME="localhost" \
	#	-e LDAP_PASSWORD="admin" \
	#	-e LOGLEVEL=INFO \
	#	--entrypoint /usr/local/bin/uvicorn \
	#	${IMAGE} code/main:app --reload --host 0.0.0.0 --port 8888
	docker \
		run --rm \
		--name scim \
		--network host \
		-v $$PWD:/app \
		-e LOGLEVEL=INFO \
		-e PYTHONPATH=/app \
		-e SCHEMA_PATH=/app/schemas \
		--entrypoint /usr/local/bin/uvicorn \
		${IMAGE} main:app --reload --host 0.0.0.0 --port 8888

push: all
	docker push ${REPOSITORY_URL}/${IMAGE}:${TAG}
