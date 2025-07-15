"""Configuration constants for the proxy server."""
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Groq API configuration
GROQ_MODEL = "moonshotai/kimi-k2-instruct"
GROQ_MAX_OUTPUT_TOKENS = 16_384  # max Groq supports
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Initialize OpenAI client for Groq
def get_groq_client() -> OpenAI:
    """Get configured OpenAI client for Groq API."""
    # Try environment variable first
    api_key = os.getenv("GROQ_API_KEY")
    
    # If not found, try to get from cache
    if not api_key:
        try:
            from .cli import get_api_key
            api_key = get_api_key()
        except ImportError:
            pass
    
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment or cache")
    
    return OpenAI(
        api_key=api_key,
        base_url=GROQ_BASE_URL
    )