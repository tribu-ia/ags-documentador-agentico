from typing import Protocol, Dict

class LanguageModel(Protocol):
    """Interface for language model interactions"""
    async def generate_content(self, prompt: str, config: Dict) -> str:
        """Generate content from prompt"""
        pass 