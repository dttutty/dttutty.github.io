#!/usr/bin/env bash

set -euo pipefail

readonly JEMDOC_COMMIT="28c8a2b7c72dae7f6b9c47a31f936c089040417a"
readonly JEMDOC_SHA256="e513fc660dc4fe27d37cc2ed68d838fe25e652cd033ee50747f09a25e7914e76"
readonly CSS_SHA256="24b5cf5358e63d3ac7a4ca22208f839f6c9f3591cf0acc6ce0e867654cfc447b"
readonly PYTHON_IMAGE="python:2.7-alpine@sha256:724d0540eb56ffaa6dd770aa13c3bc7dfc829dec561d87cb36b2f5b9ff8a760a"
readonly -a PAGES=(
  index.jemdoc
  research.jemdoc
  publications.jemdoc
  projects.jemdoc
  experience.jemdoc
  background.jemdoc
)

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="$(mktemp -d)"

cleanup() {
  rm -rf -- "${build_dir}"
}
trap cleanup EXIT

curl --fail --silent --show-error --location \
  "https://raw.githubusercontent.com/jem/jemdoc/${JEMDOC_COMMIT}/jemdoc" \
  --output "${build_dir}/jemdoc"
curl --fail --silent --show-error --location \
  "https://raw.githubusercontent.com/jem/jemdoc/${JEMDOC_COMMIT}/css/jemdoc.css" \
  --output "${build_dir}/jemdoc.css"

printf '%s  %s\n' "${JEMDOC_SHA256}" "${build_dir}/jemdoc" | sha256sum --check --status
printf '%s  %s\n' "${CSS_SHA256}" "${build_dir}/jemdoc.css" | sha256sum --check --status

cp "${build_dir}/jemdoc.css" "${repo_root}/jemdoc.css"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "${repo_root}:/site" \
  --volume "${build_dir}:/jemdoc:ro" \
  --workdir /site \
  "${PYTHON_IMAGE}" \
  python /jemdoc/jemdoc -c jemdoc.conf "${PAGES[@]}"
