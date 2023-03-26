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
	#docker run -d --name mongo -e MONGO_INITDB_ROOT_USERNAME=mongo -e MONGO_INITDB_ROOT_PASSWORD=secret  arm64v8/mongo
	#docker run -d --name mysql -e MYSQL_ROOT_PASSWORD=secret mysql:latest
	#docker run --rm --link mongo:mongo --link mysql:mysql -p 8000:80 -ti -v $$PWD/code:/code --entrypoint /usr/local/bin/uvicorn ${IMAGE} main:app --reload --host 0.0.0.0 --port 80
	docker run --rm -p 8000:80 -ti -v $$PWD/code:/code --entrypoint /usr/local/bin/uvicorn ${IMAGE} main:app --reload --host 0.0.0.0 --port 80

push: all
	docker push ${REPOSITORY_URL}/${IMAGE}:${TAG}
