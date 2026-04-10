# Wrapper Usage

This document is only about how to use the Python wrapper API.

If you want the architectural overview first, read `../README.md`.

## Mental Model

`DucklingWrapper` is a thin Python client around Duckling's HTTP API.

That means:

- you create a wrapper instance
- the wrapper builds a request payload
- the wrapper sends an HTTP request to Duckling's `/parse` endpoint
- Duckling returns JSON
- the wrapper gives that JSON back to you as Python data

The wrapper can also launch a local Duckling process for development if you already have a built Duckling checkout.

## Main API Surface

The public pieces are:

- `DucklingWrapper`
- `DucklingDefaults`
- `to_epoch_millis(...)`
- `DucklingWrapper.get_config_help()`
- `DucklingWrapper.describe_config()`

## Constructor

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper(
    host="127.0.0.1",
    port=8000,
    stack_path="stack",
    defaults=None,
    session=None,
)
```

### Constructor parameters

#### `host: str = "127.0.0.1"`

The host where Duckling is listening.

Effect on I/O:

- changes the network destination for requests
- contributes to the final parse URL: `http://{host}:{port}/parse`

Use cases:

- `127.0.0.1` for local development
- a container hostname for Docker Compose
- a service DNS name in production

#### `port: int = 8000`

The port where Duckling is listening.

Effect on I/O:

- changes the network destination for requests
- also controls which port `start_server(...)` tries to launch Duckling on

#### `stack_path: str = "stack"`

The executable name or full path for the Haskell `stack` command.

Effect on I/O:

- does nothing during normal HTTP parsing
- only matters when `start_server(...)` launches a local Duckling process

Use this if:

- `stack` is not on `PATH`
- you need a custom path such as `/usr/local/bin/stack`

#### `defaults: DucklingDefaults | None = None`

Optional initial wrapper defaults.

Effect on I/O:

- controls the default request payload fields used by future `parse(...)` calls
- also controls server startup timing behavior

If omitted, the wrapper creates a fresh `DucklingDefaults()` instance.

#### `session: requests.Session | None = None`

Optional preconfigured HTTP session.

Effect on I/O:

- controls how HTTP requests are sent
- lets you inject custom adapters, headers, proxies, retries, or mocked behavior

Most users can ignore this.

Useful for:

- tests
- advanced networking
- custom transport setup

## `DucklingDefaults`

`DucklingDefaults` stores default behavior for future parse calls and for startup checks.

```python
from qwackling import DucklingDefaults, DucklingWrapper

defaults = DucklingDefaults(
    locale="en_US",
    dims=["time"],
    tz="UTC",
)

wrapper = DucklingWrapper(defaults=defaults)
```

### Fields and meanings

#### `locale: str = "en_US"`

The default locale sent to Duckling.

Effect on I/O:

- included in every parse request unless overridden
- influences how Duckling interprets language and formatting conventions

Example:

- `en_US` for US English style parsing
- `fr_FR` for French parsing behavior

#### `lang: str | None = None`

Optional language override sent to Duckling.

Effect on I/O:

- if set, the wrapper includes `"lang"` in the request payload
- if `None`, the wrapper omits `"lang"` entirely

Use this when you want explicit language control separate from locale.

#### `dims: list[str] | None = None`

Optional list of Duckling dimensions to parse.

Effect on I/O:

- if set, the wrapper sends `"dims"` as JSON text
- if `None`, the wrapper omits `"dims"` and lets Duckling consider all dimensions

Common example:

```python
dims=["time"]
```

That narrows parsing to time-related entities.

#### `latent: bool = False`

Whether Duckling should include latent results.

Effect on I/O:

- always sent as `"true"` or `"false"` in the request payload
- influences which candidate results Duckling returns

Use this when you want less explicit or more tentative matches included.

#### `tz: str | None = None`

Optional IANA timezone name such as `UTC` or `Asia/Kolkata`.

Effect on I/O:

- if set, included in the request payload as `"tz"`
- affects how Duckling resolves time expressions

This matters for phrases like:

- `tomorrow at 8pm`
- `next Monday`
- `in 2 hours`

#### `reftime: int | None = None`

Optional reference time in Unix epoch milliseconds.

Effect on I/O:

- if set, included in the request payload as `"reftime"`
- controls what "now" means for relative expressions

This is especially important for deterministic tests.

#### `request_timeout: float = 10.0`

HTTP timeout in seconds.

Effect on I/O:

- used when the wrapper calls Duckling over HTTP
- also used by the readiness check in `is_server_ready()`

#### `startup_retries: int = 30`

How many times `start_server(...)` checks whether a newly launched local server is ready.

Effect on I/O:

- controls how long the wrapper waits for local Duckling startup

#### `startup_wait_seconds: float = 1.0`

Sleep interval between readiness checks during `start_server(...)`.

Effect on I/O:

- controls delay between startup health checks

## `config(...)`

Use `config(...)` to update wrapper defaults after construction.

```python
wrapper = DucklingWrapper().config(
    locale="en_US",
    dims=["time"],
    tz="UTC",
    request_timeout=5.0,
)
```

This mutates the wrapper's stored defaults and returns the same wrapper instance.

### Important behavior

- values set in `config(...)` become the new defaults for future `parse(...)` calls
- values set in `config(...)` also affect `start_server(...)` timing
- passing `None` for optional fields like `tz`, `reftime`, or `dims` clears them

Example:

```python
wrapper = DucklingWrapper().config(tz="UTC", dims=["time"])
wrapper.config(tz=None, dims=None)
```

After that, `tz` and `dims` are no longer sent by default.

## Config helpers

If you want users to inspect config meanings from Python instead of reading docs manually, use these helpers.

### `DucklingWrapper.get_config_help()`

Returns metadata for every constructor/config field, including:

- expected type
- default value
- which wrapper operation it affects
- a user-facing description

Example:

```python
from qwackling import DucklingWrapper

help_text = DucklingWrapper.get_config_help()
print(help_text["tz"])
```

### `DucklingWrapper.describe_config()`

Returns the same metadata plus the wrapper's current values.

Example:

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper(host="duckling", port=9000).config(
    tz="UTC",
    dims=["time"],
)

print(wrapper.describe_config()["tz"])
print(wrapper.describe_config()["host"])
```

## `parse(...)`

`parse(...)` sends a request to Duckling and returns the parsed JSON response.

```python
results = wrapper.parse("tomorrow at 8pm")
```

Signature:

```python
parse(
    text: str,
    *,
    locale: str | None = None,
    lang: str | None = None,
    dims: list[str] | None = None,
    latent: bool | None = None,
    tz: str | None = None,
    reftime: int | None = None,
) -> list[dict[str, Any]]
```

### How overrides work

Per-call arguments override wrapper defaults for that request only.

Example:

```python
wrapper = DucklingWrapper().config(locale="en_US", tz="UTC", dims=["time"])

results = wrapper.parse(
    "tomorrow at 8pm",
    locale="en_GB",
    tz="Asia/Kolkata",
)
```

In that call:

- `locale` is `en_GB`
- `tz` is `Asia/Kolkata`
- `dims` still comes from the wrapper default

### What gets sent

For a call like:

```python
wrapper = DucklingWrapper().config(
    locale="en_US",
    dims=["time"],
    latent=False,
    tz="UTC",
    reftime=1775622600000,
)

wrapper.parse("tomorrow at 8pm")
```

the wrapper sends form data shaped like:

```python
{
    "text": "tomorrow at 8pm",
    "locale": "en_US",
    "dims": "[\"time\"]",
    "latent": "false",
    "tz": "UTC",
    "reftime": "1775622600000",
}
```

Notes:

- `dims` is JSON-encoded text
- `latent` is sent as the lowercase string `"true"` or `"false"`
- `reftime` is sent as a string

### What comes back

The wrapper returns `response.json()` directly.

That means the return value is whatever Duckling returns, typically a list of dictionaries.

The wrapper does not remap Duckling's schema into custom Python classes.

## `start_server(...)`

`start_server(duckling_dir: str)` launches a local Duckling process from a Duckling source checkout.

```python
with DucklingWrapper(port=8000) as wrapper:
    wrapper.start_server("./duckling")
    results = wrapper.parse("tomorrow at 8pm")
```

### What it expects

- a valid Duckling checkout already exists
- Duckling has been built
- `stack` works

### What it does

1. sets the `PORT` environment variable
2. runs `stack exec duckling-example-exe`
3. polls `/parse` until the server responds or startup retries are exhausted

### What it does not do

- clone Duckling
- install Haskell
- build Duckling automatically

## `stop_server()`

Stops the local Duckling process started by this wrapper, if one is running.

It does nothing if the wrapper did not start a process.

## `is_server_ready()`

Checks whether Duckling is responding at the configured URL.

It sends a small POST request to `/parse` and returns:

- `True` if the server responds with HTTP 200
- `False` if the request fails or returns a different status

This is mainly useful for startup flow and debugging.

## `close()` and context-manager usage

`close()`:

- stops a managed local Duckling process if one exists
- closes the underlying HTTP session

You can call it directly:

```python
wrapper = DucklingWrapper()
try:
    ...
finally:
    wrapper.close()
```

Or use the wrapper as a context manager:

```python
with DucklingWrapper() as wrapper:
    ...
```

The context manager is the safest option if you are using `start_server(...)`.

## `to_epoch_millis(...)`

Use `to_epoch_millis(...)` when you want a safe way to create `reftime`.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from qwackling import to_epoch_millis

reftime = to_epoch_millis(
    datetime(2026, 4, 8, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
)
```

Important rule:

- the `datetime` must be timezone-aware

If it is naive, the helper raises `ValueError`.

## Usage Patterns

### 1. Simplest client usage

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper(host="127.0.0.1", port=8000)
print(wrapper.parse("tomorrow at 8pm"))
```

Use this when Duckling is already running elsewhere.

### 2. Stable defaults for many calls

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper().config(
    locale="en_US",
    dims=["time"],
    tz="UTC",
)

print(wrapper.parse("tomorrow"))
print(wrapper.parse("next Friday at 6pm"))
```

Use this when your app has a consistent parsing context.

### 3. Per-call overrides for one request

```python
results = wrapper.parse(
    "demain a 20h",
    locale="fr_FR",
    lang="FR",
    dims=["time"],
)
```

Use this when most requests share defaults, but one request needs special handling.

### 4. Deterministic testing with fixed `reftime`

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from qwackling import DucklingWrapper, to_epoch_millis

wrapper = DucklingWrapper().config(
    locale="en_US",
    tz="UTC",
    dims=["time"],
    reftime=to_epoch_millis(
        datetime(2026, 4, 8, 10, 0, tzinfo=ZoneInfo("UTC"))
    ),
)

print(wrapper.parse("tomorrow at 8pm"))
```

Use this in tests so relative date results do not drift over time.

### 5. Local development with managed startup

```python
from qwackling import DucklingWrapper

with DucklingWrapper(port=8000) as wrapper:
    wrapper.start_server("./duckling")
    print(wrapper.parse("tomorrow at 8pm"))
```

Use this only when you already have a local Duckling checkout.

## Error Expectations

### Connection errors

If no Duckling server is listening at the configured host and port, `parse(...)` will raise a `requests` connection error.

That usually means:

- Duckling is not running
- the host/port is wrong
- the service is not reachable from the current environment

### HTTP errors

If Duckling responds with an error status, `parse(...)` raises `response.raise_for_status()`.

### Startup errors

If `start_server(...)` cannot bring Duckling up before retries are exhausted, it raises:

```text
RuntimeError: Duckling server failed to start at http://...
```

## Recommended Practices

- Use `config(...)` for stable defaults your app uses repeatedly.
- Use per-call overrides only when a single request is unusual.
- Set `dims=["time"]` if you only care about time parsing.
- Set `tz` and `reftime` explicitly when deterministic relative-time behavior matters.
- Use a context manager when managing a local Duckling process.
- In production, prefer a separately managed Duckling service over `start_server(...)`.
