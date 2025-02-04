from setuptools import setup, find_packages

setup(
    name="parallama",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.4.2",
        "sqlalchemy>=2.0.23",
        "psycopg2-binary>=2.9.9",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "redis>=5.0.1",
        "httpx>=0.25.1",
        "python-multipart>=0.0.6",
        "pyyaml>=6.0.1",
        "click>=8.1.0",
        "tabulate>=0.9.0",
        "typer>=0.9.0",
        "rich>=13.7.0"
    ],
    entry_points={
        "console_scripts": [
            "parallama-cli=parallama.cli:cli",
        ],
    },
    python_requires=">=3.9",
    author="Parallama Maintainer",
    author_email="maintainer@parallama.org",
    description="Multi-user authentication and access management service for Ollama",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/parallama",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
