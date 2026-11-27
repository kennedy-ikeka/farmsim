from langchain_ollama import ChatOllama
from langchain_google_genai import GoogleGenerativeAI, ChatGoogleGenerativeAI

from src.utils.config import GOOGLE_CHAT_MODEL, OLLAMA_CHAT_MODEL, TEMPERATURE, OLLAMA_API_KEY, OLLAMA_BASE_URL, GOOGLE_API_KEY

def get_ollama_llm(model: str = OLLAMA_CHAT_MODEL, temperature: float = TEMPERATURE) -> ChatOllama:
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
    return ChatOllama(**{
        'model': model,
        'base_url': OLLAMA_BASE_URL,
        'temperature': temperature,
        'api_key': OLLAMA_API_KEY,
        'cloud': True
    })


def get_google_llm(model=GOOGLE_CHAT_MODEL, temperature: float = TEMPERATURE):
    return ChatGoogleGenerativeAI(**{
        'model': model,
        'temperature': temperature,
        'google_api_key': GOOGLE_API_KEY,
        'api_version':"v1beta"
    })