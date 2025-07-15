from setuptools import setup, find_packages

setup(
    name="cckimi",
    version="0.1.0",
    description="Claude Code Kimi-Groq Proxy",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "openai>=1.0.0",
        "pydantic>=2.0.0",
        "python-dotenv>=0.19.0",
        "rich>=12.0.0",
        "psutil>=5.8.0",
        "keyring>=23.0.0",
        "cryptography>=3.4.0",
    ],
    entry_points={
        "console_scripts": [
            "cckimi=cckimi.cli:cckimi_cli",
            "kimi=cckimi.cli:kimi_cli",
        ],
    },
    python_requires=">=3.8",
)