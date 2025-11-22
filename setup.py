from setuptools import setup, find_packages

setup(
    name="ai-agent-observatory",
    version="0.1.0",
    description="Monitoring, evaluation, and optimization platform for AI agents",
    author="Bryan",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.18.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "streamlit>=1.30.0",
        "pandas>=2.0.0",
        "plotly>=5.18.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "tiktoken>=0.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "observatory=observatory.cli:main",
        ],
    },
)