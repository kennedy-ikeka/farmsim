"""LLM and embedding configuration module.

Provides factory functions for getting LLM and embedding instances
based on environment configuration.
"""
from langchain_ollama import ChatOllama, OllamaEmbeddings
from dotenv import load_dotenv

from src.utils.config import ENV, ENVIRONMENTS, OLLAMA_BASE_URL, OLLAMA_API_KEY

def get_llm(model: str = 'glm-5.2:cloud', temperature: float = 0) -> ChatOllama:
    """Get LLM instance based on environment configuration.

    Args:
        model: Model name to use
        temperature: Sampling temperature for response generation

    Returns:
        ChatOllama LLM instance configured for environment

    Notes:
        - Uses cloud configuration for PRODUCTION and STAGING
        - Uses local Ollama for DEVELOPMENT and TESTING
    """
    config = {
        'model': model,
        'base_url': OLLAMA_BASE_URL,
        'temperature': temperature
    }

    if ENV in [ENVIRONMENTS.PRODUCTION, ENVIRONMENTS.STAGING]:
        config['cloud'] = True
        config['api_key'] = OLLAMA_API_KEY

    return ChatOllama(**config)
