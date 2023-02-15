#!/usr/bin/env bash
IMAGE="trawl:latest"
WORKDIR="trawl-data"

ENV_VARS=( \
  "TRAWL_USER" \
  "TRAWL_PASSWORD"
)

ENV_PARAM=""
for ENV_VAR in ${ENV_VARS[*]}; do
  if [[ ! -z "${!ENV_VAR}" ]]; then
    ENV_PARAM="$ENV_PARAM --env $ENV_VAR=${!ENV_VAR}"
  fi
done

if [[ ! -d "$WORKDIR" ]]; then
  mkdir "$WORKDIR"
fi

docker run -it --rm --hostname trawl $ENV_PARAM --mount type=bind,source="$(pwd)"/"$WORKDIR",target=/shared-data $IMAGE trawl "$@"
