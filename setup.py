from setuptools import setup, find_packages

setup(
    name="lightrunnercommon",
    version='0.1',
    install_requires=[
        'toml',
        'flask',
        'click',
        'requests',
        'pyyaml',
    ],
    packages=find_packages(),
)
