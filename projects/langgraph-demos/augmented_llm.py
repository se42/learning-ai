from langchain_openai.chat_models import ChatOpenAI
from pydantic import BaseModel, Field

llm = ChatOpenAI(model_name="gpt-4o-mini")

class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query that is optimized web search.")
    justification: str = Field(
        None, description="Why this query is relevant to the user's request."
    )
    tool_calls: list[str] = Field(
        None, description="List of tool calls that were made to retrieve information."
    )

def do_web_search(query: str) -> str:
    '''
    Do a web search for the given query.
    '''
    print(f"Doing web search for: {query}")
    return 'I found some great information about that!'

llm = llm.bind_tools([do_web_search])
structured_llm = llm.with_structured_output(SearchQuery)
output = structured_llm.invoke("How does Calcium CT score relate to high cholesterol? Provide up to date information.")
print(output)
