# Duckling Research Findings

## Overview
Duckling is a Haskell library by Meta (formerly Facebook) for parsing text into structured data (dates, times, amounts, etc.).

## Architecture
- Written in Haskell.
- Provides an HTTP server (`duckling-example-exe`) by default.
- API Endpoint: `POST /parse`
- Parameters:
  - `text`: The text to parse.
  - `lang`: Optional Duckling language code.
  - `locale`: e.g., `en_GB`, `en_US`.
  - `dims`: JSON array of dimensions to extract (e.g., `["time", "numeral"]`).
  - `latent`: Boolean to include latent parses.
  - `tz`: IANA timezone string such as `Asia/Kolkata`.
  - `reftime`: Unix epoch milliseconds used as Duckling's reference time.

## Existing Python Wrappers
- `duckling`: A wrapper for wit.ai's Duckling (often requires JVM or connects to a server).
- `pyduckling-native`: Native bindings (might be complex to build/maintain).
- `fb_duckling`: Another wrapper.

## Implemented Approach

1. **Server-based wrapper**: The Python package talks to Duckling's HTTP API.
2. **Client library plus optional local runtime**:
   - Use `DucklingWrapper` as a client for a running Duckling service.
   - Optionally call `start_server()` for local development.
3. **Configurable defaults**:
   - Wrapper-level defaults are stored through `config()`.
   - Per-call overrides remain available in `parse()`.
4. **Project layout**:
   - Python package code is now under `src/qwackling/`
   - A small `src/duckling_wrapper/` compatibility alias can still re-export the public API.
   - Unit tests are under `tests/`
   - Docs are under `docs/`
   - Helper commands are in `scripts/manage_wrapper.sh`
   - The helper script can clone Duckling automatically before building it locally

## Best-Practice Integration Guidance

- For production systems, run Duckling as a separate service and use this project as a pure Python client dependency.
- For local development, CI, or smaller tools, using `start_server()` from the wrapper is reasonable.
- Keep `reftime` fixed in tests when validating relative time expressions like `"tomorrow"` or `"next Friday"`.
- Prefer path or editable dependency installs while iterating locally.

## Installation Requirements
- Haskell `stack` to build Duckling.
- `pcre` development headers.
- Python `requests` for the wrapper.

## Validation Status

The current project now includes:

- packaged source layout
- installable Python metadata
- wrapper-level config defaults
- unit tests
- build and test helper script
