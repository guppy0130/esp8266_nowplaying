.PHONY: docker run-docker flask
# build server
docker:
	docker buildx build . -t esp8266_nowplaying:latest

# run it with gunicorn
run-docker:
	docker run --env-file=.env -p 5000:80 -it esp8266_nowplaying --log-level debug

clean:
	rm -rf .spotify-cache

flask:
	flask run --host=0.0.0.0
