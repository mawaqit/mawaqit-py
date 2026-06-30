import os
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()

version = os.getenv("VERSION")
if version is None:
    raise ValueError("VERSION environment variable is not set")

setup(
    name="mawaqit",
    version=version,
    author="MAWAQIT",
    author_email="support@mawaqit.net",
    description="The official MAWAQIT Python wrapper.\n"
    "Get the data of your mosque (such as name, location, prayer times) from the MAWAQIT API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mawaqit/mawaqit-py",
    project_urls={
        "Bug Tracker": "https://github.com/mawaqit/mawaqit-py/issues",
    },
    license="Apache-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    packages=find_packages(include=["mawaqit", "mawaqit.*"]),
    package_data={"mawaqit": ["py.typed"]},
    install_requires=["aiohttp>=3.8.0"],
    python_requires=">=3.10",
)
