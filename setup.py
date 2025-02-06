from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name="parallama",
        version="0.1.0",
        packages=find_packages(where="src"),
        package_dir={"": "src"},
        entry_points={
            "console_scripts": [
                "parallama-cli=parallama.cli:main",
            ],
        },
        include_package_data=True,
        data_files=[
            ('/usr/lib/systemd/system', ['systemd/parallama.service']),
        ],
        install_requires=[],  # Dependencies are handled by virtual environment
    )
