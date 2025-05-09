docker build -t wrc .
id=$(docker create wrc)
docker cp $id:/build ./build-docker
