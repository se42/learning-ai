import os
from typing import Any
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

class SimpleAI:
    """A simple AI interface for generating guest responses using a chat model."""

    def __init__(self) -> None:
        """Initialize the chat model. Raises an exception if OPENAI_API_KEY is missing."""
        if not os.environ.get("OPENAI_API_KEY"):
            raise EnvironmentError("Error: OPENAI_API_KEY not found in environment variables")
        self.model = init_chat_model("gpt-4o-mini", model_provider="openai")

    def simple_question(self, name: str, personality: str, question: str) -> Any:
        """Generate a response as if from a guest, given their name, personality, and a question.

        Args:
            name (str): The guest's name.
            personality (str): Description of the guest's personality.
            question (str): The question to ask the guest.

        Returns:
            Any: The AI-generated response object (with a .content attribute).
        """
        system_template: str = (
            f"You are {name}. {personality}\n\nAnswer all questions as {name}."
        )
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("user", "{question}")
        ])
        prompt = prompt_template.invoke({
            "name": name,
            "personality": personality,
            "question": question
        })
        response = self.model.invoke(prompt)
        return response
        