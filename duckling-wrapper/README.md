# Qwackling

`qwackling` is a Python client for Duckling's HTTP API.

The most important thing to understand is this:

- This package is the Python client.
- Duckling itself is a separate Haskell service.
- Building this Python package does not bundle, compile, or ship Duckling.

If you keep that mental model in mind, the rest of the workflow becomes much easier.

## Read This README As Two Layers

This README focuses on:

- what the wrapper really is
- how it should be integrated
- how to develop and package it

If you want API-level usage details for the wrapper itself, read:

- [`@docs/wrapper usage.md`](docs/wrapper%20usage.md)

## What This Project Actually Is

This repository contains a small Python package that sends HTTP requests to Duckling's `/parse` endpoint.

The code in this package:

- builds request payloads
- applies default parsing options like `locale`, `tz`, and `reftime`
- sends requests to a Duckling server with `requests`
- can optionally start a local Duckling process for development if you already have a Duckling checkout on disk

The code in this package does not:

- implement the Duckling parser itself
- compile Haskell code
- include the Duckling source tree in the wheel or sdist
- make Duckling magically available after `pip install`

In other words, this package is a wrapper around Duckling, not a replacement for Duckling.

## Architecture At A Glance

```text
Your Python app
    |
    v
qwackling
    |
    v
HTTP POST /parse
    |
    v
Duckling server (separate process)
```

There are two supported ways to supply that Duckling server:

1. Run Duckling as its own long-lived service and point this wrapper at it.
2. Use `DucklingWrapper.start_server(...)` to launch a local Duckling process from an existing Duckling checkout during development or tests.

For production, option 1 is the cleaner model.

## What Gets Packaged

When you run:

```bash
python -m build --no-isolation
```

the generated artifacts in `dist/` contain the Python package only:

- `qwackling`
- packaging metadata
- Python dependency declarations such as `requests`

They do not contain:

- `duckling-example-exe`
- the Duckling git repository
- the Haskell `stack` toolchain
- a prebuilt embedded parser binary

That behavior comes directly from `pyproject.toml`, which maps the `qwackling` package to the files kept directly under `src/`.

## What `start_server(...)` Really Does

`DucklingWrapper.start_server(...)` is a convenience for local development.

It does not download or build Duckling for you.

It expects:

- a Duckling source checkout already exists somewhere on disk
- `stack` is installed and usable
- `duckling-example-exe` can be launched from that checkout

What it actually does is:

1. set the `PORT` environment variable
2. run `stack exec duckling-example-exe` in the Duckling checkout directory
3. poll the configured `/parse` endpoint until the server responds

So `start_server(...)` is "process management for an existing Duckling checkout", not "install Duckling automatically".

## Choose Your Integration Model

### Option 1: Existing Duckling service

Use this when:

- your main project already runs backend services
- you want cleaner deployment boundaries
- you want one Duckling instance shared by multiple workers or apps
- you are deploying to staging or production

Example:

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper(host="127.0.0.1", port=8000)
results = wrapper.parse("tomorrow at 8pm")
print(results)
```

This is the recommended production model.

### Option 2: Start Duckling from Python for local dev/tests

Use this when:

- you are developing locally
- you want a self-contained test harness
- you already have a Duckling checkout available

Example:

```python
from qwackling import DucklingWrapper

with DucklingWrapper(port=8000) as wrapper:
    wrapper.start_server("./duckling")
    results = wrapper.parse("tomorrow at 8pm")
    print(results)
```

This is convenient, but it still depends on a separate Duckling checkout and Haskell toolchain being present.

## Install The Python Wrapper

### Runtime install

```bash
pip install .
```

### Development install

With `pip`:

```bash
python -m pip install -e ".[dev]"
```

With `uv`:

```bash
uv sync --extra dev
```

With the helper script:

```bash
./scripts/manage_wrapper.sh install-dev
```

## Build Duckling Locally

You only need this if you want to run Duckling yourself, especially through `start_server(...)`.

On Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y curl pkg-config libpcre3-dev
curl -sSL https://get.haskellstack.org/ | sh
```

Then from this package directory:

```bash
./scripts/manage_wrapper.sh build-duckling
```

That helper script:

- clones `https://github.com/facebook/duckling.git` into `./duckling` if needed
- runs `stack build` inside that checkout

The script lives at `scripts/manage_wrapper.sh`.

Or run with docker:

```bash
sudo docker run -p 8000:8000 rasa/duckling
```

## Quick Start

### Call an already-running Duckling service

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper(host="127.0.0.1", port=8000)
print(wrapper.parse("tomorrow at 8pm"))
```

### Start a local Duckling checkout from Python

```python
from qwackling import DucklingWrapper

with DucklingWrapper(port=8000) as wrapper:
    wrapper.start_server("./duckling")
    print(wrapper.parse("tomorrow at 8pm"))
```

For deeper wrapper API usage, parameter meanings, config helpers, and more examples, see:

- [`@docs/wrapper usage.md`](docs/wrapper%20usage.md)

## Configuration

The wrapper lets you set stable defaults once and then reuse them for future calls.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from qwackling import DucklingWrapper, to_epoch_millis

wrapper = DucklingWrapper().config(
    locale="en_US",
    tz="Asia/Kolkata",
    reftime=to_epoch_millis(
        datetime(2026, 4, 8, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    ),
    dims=["time"],
)

results = wrapper.parse("tomorrow at 8pm")
```

Default values:

- `locale="en_US"`
- `lang=None`
- `dims=None`
- `latent=False`
- `tz=None`
- `reftime=None`
- `request_timeout=10.0`
- `startup_retries=30`
- `startup_wait_seconds=1.0`

Notes:

- `tz` should be an IANA timezone such as `Asia/Kolkata` or `UTC`
- `reftime` must be Unix epoch milliseconds
- `to_epoch_millis(...)` requires a timezone-aware `datetime`

## How To Integrate This Into Your Main Project

If your main project needs natural-language date/time parsing, treat Duckling and this wrapper as two different dependencies:

1. your Python app dependency: `qwackling`
2. your runtime parser service: Duckling

### Recommended production integration

In a main backend project, the cleanest pattern is usually:

1. deploy Duckling as a separate service or sidecar
2. configure its host and port through environment variables
3. instantiate `DucklingWrapper` once in your app
4. call `parse(...)` wherever you need text-to-time extraction

Example:

```python
import os

from qwackling import DucklingWrapper


duckling = DucklingWrapper(
    host=os.getenv("DUCKLING_HOST", "127.0.0.1"),
    port=int(os.getenv("DUCKLING_PORT", "8000")),
).config(
    locale="en_US",
    tz="UTC",
    dims=["time"],
)


def parse_natural_language_datetime(text: str):
    return duckling.parse(text)
```

Why this is usually the best choice:

- your app and parser can scale independently
- startup is simpler and more predictable
- failures are easier to observe
- deployments do not require bundling Haskell into your Python package

### What this means in practice

If your main project is a Python app or API service, a good setup is usually:

1. add `qwackling` as a Python dependency
2. run Duckling separately as infrastructure
3. keep Duckling host and port in config or environment variables
4. create one wrapper instance at app startup
5. call `parse(...)` from your domain code

That keeps the Python package lightweight and keeps the Haskell runtime out of your Python build process.

### Good local development pattern

For local development, you can either:

- run Duckling separately in another terminal, or
- let tests/dev scripts call `start_server(...)`

That keeps production simple while still making local iteration easy.

### Good testing pattern

For unit tests in your main project:

- mock the wrapper or the HTTP boundary
- avoid depending on a real Duckling process unless the test is specifically integration-level

For integration tests:

- start a real Duckling instance
- use fixed `reftime` values so relative expressions stay deterministic

## What To Put In Your Main Project Docs

If you adopt this package in another repo, document it in these terms:

- "We use `qwackling` as the Python client."
- "We run Duckling as a separate service."
- "The Python dependency does not include the Duckling executable."

That one clarification prevents most setup confusion.

## Common Misunderstanding

If someone does this:

```bash
pip install qwackling
python app.py
```

and expects parsing to work immediately, they will usually get a connection error.

That does not mean the Python package is broken.

It usually means no Duckling server is listening yet.

The correct fix is one of:

- start Duckling separately and point the wrapper at it
- build a local Duckling checkout and call `start_server(...)`

## Wrapper Development

If you are developing this wrapper package itself, think of the work in three separate areas:

1. Python wrapper code
2. optional local Duckling runtime for integration-style workflows
3. packaging and publishing

### Python wrapper code

The Python package source lives under:

- `src/`

That is the code that gets built into the Python distribution.

Tests live under:

- `tests/`

### Local Duckling runtime

The local Duckling checkout is only a helper for development and manual/integration testing.

It is not part of the Python package source tree even if it exists at:

- `./duckling`

If that directory exists, it is a runtime helper checkout, not packaged library code.

### Development install

For active wrapper development:

```bash
python -m pip install -e ".[dev]"
```

Or:

```bash
uv sync --extra dev
```

### Development workflow

A practical flow for wrapper development is:

1. edit code under `src/`
2. run unit tests
3. if needed, build Duckling locally for manual validation
4. build the Python package
5. install that package into another project for verification

## Build

Create source and wheel distributions:

```bash
python -m build --no-isolation
```

Or:

```bash
./scripts/manage_wrapper.sh build
```

Artifacts are written to `dist/`, for example:

```text
dist/qwackling-0.1.1-py3-none-any.whl
dist/qwackling-0.1.1.tar.gz
```

### What the build output contains

The package build contains:

- Python wrapper source
- package metadata
- declared Python dependencies

The package build does not contain:

- Duckling source code
- a compiled Duckling executable
- the Haskell toolchain
- a local `./duckling` checkout

That separation is intentional.

## Tests

Run the unit tests after a dev install:

```bash
python -m pytest -c pyproject.toml tests
```

Or:

```bash
./scripts/manage_wrapper.sh test
```

The current tests cover:

- wrapper defaults
- per-call overrides
- payload generation
- clearing optional config
- local server startup success and failure paths
- timezone-aware datetime conversion

Unit tests validate wrapper behavior. They do not prove that Duckling is installed on a target machine.

If you want end-to-end confidence, run an integration flow against a real Duckling server as a separate step.

## Integrate From Another Project

### Add as a local path dependency

With `uv`:

```bash
uv add /absolute/path/to/qwackling
```

With `pip`:

```bash
pip install /absolute/path/to/qwackling
```

### Install from a built wheel

```bash
python -m build --no-isolation
pip install /absolute/path/to/qwackling/dist/qwackling-0.1.1-py3-none-any.whl
```

### Editable install while actively developing the wrapper

```bash
pip install -e /absolute/path/to/qwackling
```

This is the best option when your main project and the wrapper are evolving together locally.

## Publish To PyPI

Build distributions:

```bash
python -m build --no-isolation
```

Validate them:

```bash
python -m twine check dist/*
```

Upload to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

Verify installation:

```bash
pip install --index-url https://test.pypi.org/simple/ qwackling
```

Publish to PyPI:

```bash
python -m twine upload dist/*
```

## Helper Script Commands

```bash
./scripts/manage_wrapper.sh all
./scripts/manage_wrapper.sh install-dev
./scripts/manage_wrapper.sh build-duckling
./scripts/manage_wrapper.sh test
./scripts/manage_wrapper.sh build
./scripts/manage_wrapper.sh clean
```

`all` is a convenience workflow for wrapper development. It installs dev dependencies, builds Duckling locally, runs tests, and builds the Python package.

## Short Version

If you only remember four things, remember these:

1. `qwackling` is a Python client, not the parser itself.
2. `python -m build` packages only the Python wrapper.
3. Duckling must exist as a separate running service or local checkout.
4. For a main production app, run Duckling separately and use this package as the client.
