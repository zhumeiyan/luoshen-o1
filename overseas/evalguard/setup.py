from setuptools import setup, find_packages
setup(
    name="evalguard",
    version="0.2.0",
    description="Static linter for LLM/agent evaluation scripts, backed by a 368-entry empirical failure-mode canon",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={"console_scripts": ["evalguard=evalguard.cli:main"]},
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Quality Assurance",
        "Intended Audience :: Developers",
    ],
)
