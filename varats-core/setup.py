from setuptools import find_namespace_packages, setup

setup(
    name='varats-core',
    version="9.0.2",
    url='https://github.com/se-passau/vara-tool-suite',
    packages=find_namespace_packages(include=['varats.*']),
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "benchbuild>=5.2",
    ],
    author="Florian Sattler",
    author_email="sattlerf@cs.uni-saarland.de",
    python_requires='>=3.6'
)
