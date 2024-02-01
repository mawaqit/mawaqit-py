from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()

setup(
    name="mawaqit",
    version="0.0.4",
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
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(include=["mawaqit", "mawaqit.*"]),
    install_requires=['aiohttp>=3.8.0',
                      'backoff>=2.0.0'],
    python_requires=">=3.7"
)