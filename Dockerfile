# OPTIONAL — only if your service needs config files shipped from git.
#
# Dokploy clears the cloned repo dir on each deploy, so runtime bind-mounts of
# repo files are unreliable. Baking config into the image at build time (the build
# context is the freshly cloned repo) is the reliable way to keep config as code.
#
# To use: put files under config/ and set `build: .` (instead of `image:`) in
# docker-compose.yml. If your service needs no shipped config, delete this file
# and the config/ directory.

# TODO: pin a real upstream image + version.
FROM REPLACE_ME/IMAGE:1.0.0

# Ship code-managed config into the image. TODO: adjust target path.
COPY config/ /etc/REPLACE_ME/

# The base image's entrypoint/cmd usually stays as-is; override via compose
# `command:` if your service needs a flag to point at the config.
