"""Setup configuration for VAST Client package."""

from setuptools import find_packages, setup


with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vast-client",
    version="1.0.0",
    author="CTV Middleware Team",
    author_email="dev@ctv-middleware.com",
    description="A modular VAST (Video Ad Serving Template) client implementation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ormwish/zbst-middleware",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Multimedia :: Video :: Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.24.0",
        "lxml>=4.9.0",
        "structlog>=22.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vast-client=vast_client.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
