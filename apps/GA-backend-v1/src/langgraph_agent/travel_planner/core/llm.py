from langchain_openai import ChatOpenAI
from src.config import TravelPlannerConfig

def get_llm(*, streaming: bool = True):
    return ChatOpenAI(
        model_name=TravelPlannerConfig.LLMConfig.MODEL_NAME,
        openai_api_key=TravelPlannerConfig.LLMConfig.API_KEY,
        openai_api_base=TravelPlannerConfig.LLMConfig.API_BASE_URL,
        temperature=0.6,
        max_tokens=4000,
        timeout=30.0,
        streaming=streaming
    )

# TODO: MUITPLE AGENTS SHOULD USE ONE LLM INSTANCE?
llm = get_llm(streaming=True)
llm_no_stream = get_llm(streaming=False)
