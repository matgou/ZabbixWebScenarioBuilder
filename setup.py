import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="zabbix_webscenario-pkg-matgou", # Replace with your own username
    version="0.0.1",
    author="Mathieu GOULIN",
    author_email="mathieu.goulin@gadz.org",
    description="An EDI to help to build zabbix webscenario",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/matgou/zabbix_webscenario_builder",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'mitmproxy',
        'simplejson',
    ],
    python_requires='>=3.6',
)