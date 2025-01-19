from enum import Enum
import logging
from functools import lru_cache
from urllib.parse import urlparse
import httpx
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_vertexai import ChatVertexAI
from app.config.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMType(str, Enum):
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    AZURE_OPENAI = "azure-gpt-4o"
    ANTHROPIC_CLAUDE = "claude-3-5-sonnet-20240620"
    GEMINI = "gemini-2.0-flash-exp"


@lru_cache(maxsize=4)
def get_openai_llm(model: str = "gpt-4o-mini", azure: bool = False):
    """Get OpenAI LLM instance"""
    if not azure:
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=0,
            )
            return llm
        except Exception as e:
            logger.error(f"Failed to instantiate ChatOpenAI due to: {str(e)}.")
            raise
    else:
        llm = AzureChatOpenAI(
            temperature=0,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            openai_api_base=settings.AZURE_OPENAI_API_BASE,
            openai_api_version=settings.AZURE_OPENAI_API_VERSION,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
        )
        return llm

@lru_cache(maxsize=2)
def get_anthropic_llm():
    """Get Anthropic Claude instance"""
    return ChatAnthropic(
        model_name="claude-3-sonnet-20240229",
        temperature=0,
    )


@lru_cache(maxsize=1)
def get_google_llm():
    """Get Google Vertex AI instance"""
    return ChatVertexAI(
        model_name="gemini-pro",
        convert_system_message_to_human=True,
        streaming=True,
    )


def get_llm(llm_type: LLMType):
    """Get LLM instance based on type"""
    if llm_type == LLMType.GPT_4O_MINI:
        return get_openai_llm()
    elif llm_type == LLMType.GPT_4O:
        return get_openai_llm(model="gpt-4o")
    elif llm_type == LLMType.AZURE_OPENAI:
        return get_openai_llm(azure=True)
    elif llm_type == LLMType.ANTHROPIC_CLAUDE:
        return get_anthropic_llm()
    elif llm_type == LLMType.GEMINI:
        return get_google_llm()
    else:
        raise ValueError(f"Unexpected LLM type: {llm_type}")