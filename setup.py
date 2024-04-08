# -*- coding:utf-8 -*-

from setuptools import setup


with open("README.md") as f2:
    LONG_DESCRIPTION = f2.read()

kw = {
    "version": "1.0.1",
    "name": "ark-mainsail",
    "keywords": ["api", "ark", "blockchain"],
    "author": "Toons",
    "author_email": "moustikitos@gmail.com",
    "maintainer": "Toons",
    "maintainer_email": "moustikitos@gmail.com",
    "url": "https://github.com/Moustikitos/python-mainsail",
    "project_urls": {  # Optional
        "Bug Reports": "https://github.com/Moustikitos/python-mainsail/issues",
        "Funding": "https://github.com/Moustikitos/python-mainsail?tab=readme-ov-file#support-this-project",
        "Source": "https://github.com/Moustikitos/python-mainsail/",
    },
    "include_package_data": True,
    "description": "Interact with ARK blockchain and forks",
    "long_description": LONG_DESCRIPTION,
    "long_description_content_type": "text/markdown",
    "install_requires": ["requests", "base58", "pyaes", "blspy", "cSecp256k1"],
    "license": "Copyright 2024, MIT licence",
    "classifiers": [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    "package_dir": {"": "."}
}

setup(**kw)
