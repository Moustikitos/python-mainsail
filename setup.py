# -*- coding:utf-8 -*-

from setuptools import setup


with open("README.md") as f2:
    LONG_DESCRIPTION = f2.read()

kw = {
    "version": "1.1.3",
    "name": "ark-mainsail",
    "keywords": ["api", "ark", "blockchain"],
    "author": "Toons",
    "author_email": "moustikitos@gmail.com",
    "maintainer": "Toons",
    "maintainer_email": "moustikitos@gmail.com",
    "url": "https://github.com/Moustikitos/python-mainsail",
    "project_urls": {  # Optional
        "Bug Reports": "https://github.com/Moustikitos/python-mainsail/issues",
        "Funding":
            "https://github.com/Moustikitos/python-mainsail?tab=readme-ov-file"
            "#support-this-project",
        "Source": "https://github.com/Moustikitos/python-mainsail/",
    },
    "include_package_data": False,
    "description": "Interact with ARK blockchain and forks",
    "long_description": LONG_DESCRIPTION,
    "long_description_content_type": "text/markdown",
    "install_requires": [
        "requests==2.31.0",
        "base58==2.1.1",
        "pyaes==1.6.1",
        "blspy==2.0.3",
        "cSecp256k1==1.1.2"
    ],
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
    "package_dir": {"": "."},
    "entry_points": {
        'console_scripts': [
            'set_validator = pool.biom:set_delegate'
        ]
    },
    "zip-safe": True
}

setup(**kw)
