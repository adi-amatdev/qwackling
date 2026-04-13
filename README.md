# Repository Layout

This workspace is centered around a single package:

- `duckling-wrapper/` — the **source of truth**

Everything related to the project lives inside that directory:

- package source code  
- tests  
- build & install commands  
- integration guidance  
- publishing workflow  

---

## Quick Start

```bash
cd duckling-wrapper
python -m pip install -e ".[dev]"
python -m pytest -c pyproject.toml tests
```

Build the package:

```bash
python -m build --no-isolation
```

---

## Minimal API Examples

### 1. Use with an existing Duckling service (recommended)

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper(host="127.0.0.1", port=8000)
print(wrapper.parse("tomorrow at 8pm"))
```

---

### 2. Configure defaults once

```python
from qwackling import DucklingWrapper

wrapper = DucklingWrapper().config(
    locale="en_US",
    tz="Asia/Kolkata",
    dims=["time"],
)

print(wrapper.parse("next friday at 6pm"))
```

---

### 3. Override per request

```python
results = wrapper.parse(
    "demain à 20h",
    locale="fr_FR",
    dims=["time"],
)
```

---

### 4. Deterministic parsing (tests)

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from qwackling import DucklingWrapper, to_epoch_millis

wrapper = DucklingWrapper().config(
    tz="UTC",
    dims=["time"],
    reftime=to_epoch_millis(
        datetime(2026, 4, 8, 10, 0, tzinfo=ZoneInfo("UTC"))
    ),
)

print(wrapper.parse("tomorrow at 8pm"))
```

---

### 5. Start a local Duckling instance (dev only)

```python
from qwackling import DucklingWrapper

with DucklingWrapper(port=8000) as wrapper:
    wrapper.start_server("./duckling")
    print(wrapper.parse("tomorrow at 8pm"))
```

---

## Good to Know

- This repository contains a **Python client**, not the Duckling parser itself  
- Duckling must be running separately for parsing to work  
- `start_server(...)` only works if you already have a built Duckling checkout  
- The Python package build includes:
  - wrapper code  
  - metadata and dependencies  
- It does not include:
  - Duckling source  
  - Haskell toolchain  
  - compiled binaries  

- Recommended production setup:
  - run Duckling as a separate service  
  - use this package as a client  

- If you get connection errors, the most common cause is:
  - Duckling is not running at the configured host/port  

---

## Where to Go Next

- Full documentation:  
  → [duckling-wrapper/README.md](duckling-wrapper/README.md)

- Detailed API usage:  
  → [duckling-wrapper/docs/](duckling-wrapper/docs/wrapper_usage.md)

---

## Mental Model

```
Your App → qwackling → HTTP → Duckling server
```