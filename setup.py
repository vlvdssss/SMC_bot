from setuptools import setup, find_packages

setup(
    name="baza-trading-bot",
    version="1.0.0",
    author="Vladyslav Kramarenko",
    description="Автоматическая торговая система на основе Smart Money Concepts",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/YOUR_USERNAME/BAZA",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "MetaTrader5>=5.0.45",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8.2",
    ],
    entry_points={
        "console_scripts": [
            "baza=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)