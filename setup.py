import setuptools

with open("README.md") as f:
    desc = f.read()

with open("VERSION") as version_file:
    version = version_file.read().strip()

install_requires = [
    "click==8.1.3",
    "boto3==1.24.14",
    "python-dotenv==0.20.0",
]

setuptools.setup(
    name="csdap-delivery-auth",
    description="A script to manage CSDAP Delivery accounts, including retrieving AWS Credentials.",
    long_description=desc,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="STAC FastAPI",
    author="Edward Keeble",
    author_email="edward@developmentseed.org",
    url="https://github.com/NASA-IMPACT/csdap-stac-api",
    license="",
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "csdap-auth = csdap_delivery_auth.cli:cli",
        ],
    },
    version=version,
)