# Same base: fixing the Dockerfile does not fix packages inside that base.
FROM ghcr.io/tommmdl/docker-lab@sha256:d8fdaffb99e0ac514b9e031ac9204b89fc2702112d198d1bebedd9d351fd19f0
USER 10001:10001
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=2)"
