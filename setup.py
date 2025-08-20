#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# READMEファイルを読み込み
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# requirements.txtから依存関係を読み込み
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="teststat-cli",
    version="1.0.0",
    description="Excelテスト仕様書からテスト結果を集計するCLIツール",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="TestStat-CLI Team",
    author_email="",
    url="",
    packages=find_packages(),
    py_modules=["test_stat_cli"],
    include_package_data=True,
    package_data={
        "": ["*.json", "*.txt", "*.yaml", "*.yml"],
        "utils": ["*.py"],
    },
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "tstat=test_stat_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    keywords="excel, testing, cli, statistics, reporting, xlsx",
    project_urls={
        "Bug Reports": "",
        "Source": "",
        "Documentation": "",
    },
)
