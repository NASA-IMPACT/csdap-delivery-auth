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

extra_reqs = {
    "dev": ["black==22.3.0", "flake8==4.0.1", "pyright==1.1.251"],
}

setuptools.setup(
    name="csdap-delivery-auth",
    description=(
        "A script to manage CSDAP Delivery accounts, including retrieving AWS"
        " Credentials."
    ),
    long_description=desc,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    author="NASA IMPACT",
    author_email="csdap@uah.edu",
    maintainer="Edward Keeble",
    maintainer_email="edward@developmentseed.org",
    url="https://github.com/NASA-IMPACT/csdap-delivery-auth",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extra_reqs,
    entry_points={
        "console_scripts": [
            "csdap-auth = csdap_delivery_auth.cli:cli",
        ],
    },
    version=version,
)
