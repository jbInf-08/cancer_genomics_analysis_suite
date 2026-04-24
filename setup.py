#!/usr/bin/env python3
"""
Setup script for Cancer Genomics Analysis Suite.

This setup script provides backward compatibility for pip installations
while the primary configuration is handled by pyproject.toml.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Cancer Genomics Analysis Suite - A comprehensive platform for cancer genomics analysis"

# Read requirements from pyproject.toml or requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "CancerGenomicsSuite", "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

if __name__ == "__main__":
    setup(
        # This setup.py is for backward compatibility only
        # The main configuration is in pyproject.toml
        setup_requires=["setuptools>=61.0", "wheel"],
        packages=find_packages(),
        package_data={
            "CancerGenomicsSuite": [
                "data/*",
                "templates/*",
                "static/*",
                "*.yaml",
                "*.yml",
                "*.json",
                "*.md",
            ]
        },
        include_package_data=True,
        zip_safe=False,
    )
