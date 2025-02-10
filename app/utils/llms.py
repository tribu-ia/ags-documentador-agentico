"""
LLM Manager Module - Centralized management of Language Models

This module provides a unified interface for managing different Language Model providers
including OpenAI, Anthropic, and Google Vertex AI. It includes:
- LLM type definitions
- Provider-specific configurations
- Caching mechanisms
- Error handling
- Logging
"""

from enum import Enum
import logging
from functools import lru_cache
from typing import Optional, Union
from urllib.parse import urlparse

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_vertexai import ChatVertexAI
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMType(str, Enum):
    """Supported LLM types with their corresponding model identifiers"""
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    AZURE_OPENAI = "azure-gpt-4o"
    ANTHROPIC_CLAUDE = "claude-3-5-sonnet-20240620"
    GEMINI = "gemini-2.0-flash-exp"

    @classmethod
    def get_default(cls) -> "LLMType":
        """Get the default LLM type"""
        return cls.GPT_4O_MINI


class LLMConfig(BaseModel):
    """Configuration for LLM instances"""
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    streaming: bool = Field(default=True)
    max_tokens: Optional[int] = Field(default=None)

    # Azure specific settings
    azure_deployment_name: Optional[str] = None
    azure_api_base: Optional[str] = None
    azure_api_version: Optional[str] = None
    azure_api_key: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class LLMManager:
    """Manager class for handling different LLM providers"""

    def __init__(self, config: LLMConfig = LLMConfig()):
        self.config = config
        self._callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

    @lru_cache(maxsize=4)
    def get_openai_llm(self, model: str = "gpt-4o-mini", azure: bool = False) -> Union[ChatOpenAI, AzureChatOpenAI]:
        """
        Get an OpenAI LLM instance with caching

        Args:
            model: The model identifier to use
            azure: Whether to use Azure OpenAI

        Returns:
            ChatOpenAI or AzureChatOpenAI instance

        Raises:
            ValueError: If Azure is requested but configuration is incomplete
            Exception: For other initialization errors
        """
        try:
            if not azure:
                return ChatOpenAI(
                    model=model,
                    temperature=self.config.temperature,
                    streaming=self.config.streaming,
                    max_tokens=self.config.max_tokens,
                    callback_manager=self._callback_manager
                )

            if not all([
                self.config.azure_deployment_name,
                self.config.azure_api_base,
                self.config.azure_api_version,
                self.config.azure_api_key
            ]):
                raise ValueError("Incomplete Azure configuration")

            return AzureChatOpenAI(
                deployment_name=self.config.azure_deployment_name,
                openai_api_base=self.config.azure_api_base,
                openai_api_version=self.config.azure_api_version,
                openai_api_key=self.config.azure_api_key,
                temperature=self.config.temperature,
                streaming=self.config.streaming,
                max_tokens=self.config.max_tokens,
                callback_manager=self._callback_manager
            )

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI LLM: {str(e)}")
            raise

    @lru_cache(maxsize=2)
    def get_anthropic_llm(self) -> ChatAnthropic:
        """
        Get an Anthropic Claude instance with caching

        Returns:
            ChatAnthropic instance

        Raises:
            Exception: For initialization errors
        """
        try:
            return ChatAnthropic(
                model_name="claude-3-5-sonnet-20240620",
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                streaming=self.config.streaming,
                callback_manager=self._callback_manager
            )
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic LLM: {str(e)}")
            raise

    @lru_cache(maxsize=1)
    def get_google_llm(self) -> ChatVertexAI:
        """
        Get a Google Vertex AI instance with caching

        Returns:
            ChatVertexAI instance

        Raises:
            Exception: For initialization errors
        """
        try:
            return ChatVertexAI(
                model_name="gemini-2.0-flash-exp",
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                streaming=self.config.streaming,
                convert_system_message_to_human=True,
                callback_manager=self._callback_manager
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google Vertex AI LLM: {str(e)}")
            raise

    def get_llm(self, llm_type: LLMType) -> Union[ChatOpenAI, AzureChatOpenAI, ChatAnthropic, ChatVertexAI]:
        """
        Get an LLM instance based on the specified type

        Args:
            llm_type: The type of LLM to initialize

        Returns:
            An initialized LLM instance

        Raises:
            ValueError: For unknown LLM types
            Exception: For initialization errors
        """
        try:
            if llm_type == LLMType.GPT_4O_MINI:
                return self.get_openai_llm()
            elif llm_type == LLMType.GPT_4O:
                return self.get_openai_llm(model="gpt-4o")
            elif llm_type == LLMType.AZURE_OPENAI:
                return self.get_openai_llm(azure=True)
            elif llm_type == LLMType.ANTHROPIC_CLAUDE:
                return self.get_anthropic_llm()
            elif llm_type == LLMType.GEMINI:
                return self.get_google_llm()
            else:
                raise ValueError(f"Unknown LLM type: {llm_type}")

        except Exception as e:
            logger.error(f"Failed to get LLM instance for type {llm_type}: {str(e)}")
            raise

    def clear_caches(self):
        """Clear all LLM instance caches"""
        self.get_openai_llm.cache_clear()
        self.get_anthropic_llm.cache_clear()
        self.get_google_llm.cache_clear()


# Example usage
def get_default_llm(config: Optional[LLMConfig] = None) -> Union[
    ChatOpenAI, AzureChatOpenAI, ChatAnthropic, ChatVertexAI]:
    """
    Get a default LLM instance with optional configuration

    Args:
        config: Optional configuration for the LLM

    Returns:
        An initialized LLM instance using default settings
    """
    manager = LLMManager(config or LLMConfig())
    return manager.get_llm(LLMType.get_default())