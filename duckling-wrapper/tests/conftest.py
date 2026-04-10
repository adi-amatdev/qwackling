from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_flat_qwackling_package() -> None:
    if "qwackling" in sys.modules:
        return

    package_dir = Path(__file__).resolve().parents[1] / "src"
    spec = importlib.util.spec_from_file_location(
        "qwackling",
        package_dir / "__init__.py",
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the qwackling package from duckling-wrapper/src")

    module = importlib.util.module_from_spec(spec)
    sys.modules["qwackling"] = module
    spec.loader.exec_module(module)


_load_flat_qwackling_package()
