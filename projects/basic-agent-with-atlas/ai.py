import os

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not found in environment variables")
    exit(1)

class SimpleAI:
    def __init__(self):
        self.model = init_chat_model("gpt-4o-mini", model_provider="openai")
    
    def simple_question(self, name, personality, question):
        system_template = f"""
        You are {name}. {personality}

        Answer all questions as {name}.
        """

        prompt_template = ChatPromptTemplate.from_messages(
            [("system", system_template), ("user", "{question}")]
        )
        prompt = prompt_template.invoke({
            "name": name,
            "personality": personality,
            "question": question
        })

        response = self.model.invoke(prompt)
        return response
        