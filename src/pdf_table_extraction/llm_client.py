from __future__ import annotations

from typing import Any, Dict, List, Optional

from groq import Groq

from .config import LLMConfig
from .utils import logger, PromptLogger

ChatMessage = Dict[str, str]


class LLMClient:
    def __init__(self, config: LLMConfig, prompt_logger: PromptLogger | None = None) -> None:
        self.config = config
        self.prompt_logger = prompt_logger or PromptLogger()
        
        # Initialize multiple Groq clients for failover
        self._groq_clients = []
        for api_key in config.get_groq_api_keys():
            self._groq_clients.append(Groq(api_key=api_key))
        
        if not self._groq_clients:
            raise ValueError("At least one GROQ_API_KEY must be configured")
        
        self._current_groq_index = 0

    def chat(self, messages: List[ChatMessage], *, model: Optional[str] = None, metadata: Dict[str, Any] | None = None) -> str:
        model_name = model or self.config.primary_model
        content = self._call_groq_with_failover(model_name, messages)
        
        content = content or ""
        prompt_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        log_path = self.prompt_logger.log(prompt=prompt_text, response=content, metadata=metadata)
        logger.info(f"Prompt logged at {log_path}")
        return content
    
    def _call_groq_with_failover(self, model_name: str, messages: List[ChatMessage]) -> str:
        """Call Groq API with automatic failover to backup keys"""
        last_error = None
        daily_limit_hit = False
        
        # Try all available Groq API keys
        for attempt in range(len(self._groq_clients)):
            client_index = (self._current_groq_index + attempt) % len(self._groq_clients)
            client = self._groq_clients[client_index]
            
            try:
                logger.info(f"Calling groq model {model_name} (API key #{client_index + 1})")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_output_tokens,
                )
                
                # Success! Update current index for next call
                self._current_groq_index = client_index
                return response.choices[0].message.content
                
            except Exception as e:
                error_msg = str(e)
                last_error = e
                
                # Check if it's a rate limit error
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    # Check if it's daily token limit (TPD = Tokens Per Day)
                    if "TPD" in error_msg or "tokens per day" in error_msg.lower():
                        daily_limit_hit = True
                        logger.warning(f"Daily token limit hit on Groq API key #{client_index + 1}, trying next key...")
                    else:
                        logger.warning(f"Rate limit hit on Groq API key #{client_index + 1}, trying next key...")
                    continue
                else:
                    # For non-rate-limit errors, raise immediately
                    logger.error(f"Error with Groq API key #{client_index + 1}: {error_msg}")
                    raise
        
        # All API keys failed
        logger.error(f"All Groq API keys exhausted. Last error: {last_error}")
        
        if daily_limit_hit:
            raise Exception(
                f"All Groq API keys have reached their DAILY token limit (100,000 tokens/day). "
                f"Please wait until the limit resets (typically at midnight UTC) or upgrade to a paid tier at "
                f"https://console.groq.com/settings/billing"
            )
        else:
            raise Exception(
                f"All Groq API keys failed due to rate limits. Please wait a minute and try again. "
                f"Last error: {last_error}"
            )
    

__all__ = ["LLMClient"]
