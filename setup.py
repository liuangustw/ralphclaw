"""Setup script for Amazon Product Monitor"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="amazon-product-monitor",
    version="0.1.0",
    author="Candice",
    description="CLI tool to monitor and discover trending products on Amazon",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
    ],
)
