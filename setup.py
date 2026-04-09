from pathlib import Path

from setuptools import find_packages, setup


ROOT = Path(__file__).parent
README = ROOT / "duckling-wrapper" / "README.md"


setup(
    name="qwackling",
    version="0.1.1",
    description="Python wrapper around Duckling's HTTP API with optional local server management.",
    long_description=README.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Aaditya",
    license="MIT",
    python_requires=">=3.10",
    package_dir={"": "duckling-wrapper/src"},
    packages=find_packages(where="duckling-wrapper/src"),
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "build>=1.2.2",
            "pytest>=8.0.0",
            "setuptools>=59.6",
            "twine>=5.1.1",
            "wheel",
        ]
    },
)
