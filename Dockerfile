FROM python:3.11-alpine AS build

WORKDIR /build

RUN apk update && apk upgrade && apk add --no-cache git && \
    pip install --no-cache-dir --upgrade pip setuptools wheel build && \
    git clone https://github.com/reismarcelo/trawl.git && \
    python3 -m build trawl

FROM python:3.11-alpine

COPY --from=build /build/trawl/dist /trawl-wheel

RUN apk update && apk upgrade && apk add --no-cache bash && \
    pip install --no-cache-dir --upgrade pip setuptools netmiko PyYAML pydantic && \
    pip install --no-cache-dir --upgrade --no-index --find-links /trawl-wheel trawl

VOLUME /shared-data

WORKDIR /shared-data

CMD ["/bin/bash"]
