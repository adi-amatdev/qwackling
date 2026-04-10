#!/usr/bin/env bash

set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${PACKAGE_DIR}/.." && pwd)"
PACKAGE_SRC_DIR="${PACKAGE_DIR}/src"
DUCKLING_DIR="${PACKAGE_DIR}/duckling"
DUCKLING_REPO_URL="${DUCKLING_REPO_URL:-https://github.com/facebook/duckling.git}"
if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif [ -x "${PACKAGE_DIR}/.venv/bin/python" ]; then
  PYTHON_BIN="${PACKAGE_DIR}/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi
SYSTEM_PYTHON_BIN="python3"
cd "$REPO_ROOT"

have_uv() {
  command -v uv >/dev/null 2>&1
}

ensure_duckling_repo() {
  if [ -d "${DUCKLING_DIR}/.git" ]; then
    return
  fi

  if [ -e "${DUCKLING_DIR}" ] && [ ! -d "${DUCKLING_DIR}/.git" ]; then
    echo "Expected ${DUCKLING_DIR} to be a git checkout, but it is not."
    echo "Remove it or set DUCKLING_DIR in the script before retrying."
    exit 1
  fi

  git clone "${DUCKLING_REPO_URL}" "${DUCKLING_DIR}"
}

build_duckling() {
  ensure_duckling_repo
  (
    cd "${DUCKLING_DIR}"
    stack build
  )
}

install_dev() {
  if have_uv; then
    uv sync --extra dev
  else
    "${PYTHON_BIN}" -m pip install -e "${REPO_ROOT}[dev]"
  fi
}

run_tests() {
  if "${PYTHON_BIN}" -m pytest --version >/dev/null 2>&1; then
    (
      cd "${PACKAGE_DIR}"
      "${PYTHON_BIN}" -m pytest -c "${REPO_ROOT}/pyproject.toml" "${PACKAGE_DIR}/tests"
    )
  elif have_uv; then
    (
      cd "${PACKAGE_DIR}"
      UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" \
        uv run --project "${REPO_ROOT}" python -m pytest -c "${REPO_ROOT}/pyproject.toml" "${PACKAGE_DIR}/tests"
    )
  else
    echo "pytest is not installed for ${PYTHON_BIN}." >&2
    echo "Run ./scripts/manage_wrapper.sh install-dev first." >&2
    exit 1
  fi
}

build_dist() {
  rm -rf "${REPO_ROOT}/build" "${REPO_ROOT}/dist"

  if "${PYTHON_BIN}" -c "import build.__main__, setuptools, wheel" >/dev/null 2>&1; then
    "${PYTHON_BIN}" -m build --no-isolation "${REPO_ROOT}"
  elif "${PYTHON_BIN}" -c "import setuptools, wheel" >/dev/null 2>&1 && [ -f "${REPO_ROOT}/setup.py" ]; then
    "${PYTHON_BIN}" setup.py sdist bdist_wheel
  elif "${SYSTEM_PYTHON_BIN}" -c "import setuptools, wheel" >/dev/null 2>&1 && [ -f "${REPO_ROOT}/setup.py" ]; then
    "${SYSTEM_PYTHON_BIN}" setup.py sdist bdist_wheel
  elif have_uv; then
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv build --project "${REPO_ROOT}"
  else
    echo "The build frontend is not installed for ${PYTHON_BIN} and uv is unavailable." >&2
    echo "Run ./scripts/manage_wrapper.sh install-dev first." >&2
    exit 1
  fi

}

bootstrap_all() {
  install_dev
  build_duckling
  run_tests
  build_dist
}

clean_artifacts() {
  rm -rf "${REPO_ROOT}/build" "${REPO_ROOT}/dist"
  find "${PACKAGE_DIR}" -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name "*.egg-info" \) -prune -exec rm -rf {} +
}

usage() {
  cat <<'EOF'
Usage: ./scripts/manage_wrapper.sh <command>

Commands:
  install-dev   Install the package in editable mode with dev dependencies
  all           Run install-dev, build-duckling, test, and build
  build-duckling Clone Duckling if needed, then build duckling-example-exe
  test          Run the unit test suite
  build         Build source and wheel distributions
  clean         Remove generated build and test artifacts
EOF
}

case "${1:-}" in
  install-dev)
    install_dev
    ;;
  all)
    bootstrap_all
    ;;
  build-duckling)
    build_duckling
    ;;
  test)
    run_tests
    ;;
  build)
    build_dist
    ;;
  clean)
    clean_artifacts
    ;;
  *)
    usage
    exit 1
    ;;
esac
