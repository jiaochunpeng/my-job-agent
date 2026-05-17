from agent_commons.llm import LLMClient


def get_llm_client(model: str = None, api_key: str = None, base_url: str = None) -> LLMClient:
    return LLMClient(model=model, api_key=api_key, base_url=base_url)
