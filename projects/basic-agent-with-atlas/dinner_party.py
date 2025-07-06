"""Module to manage dinner party simulation."""
import json
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model

from dinner_party_db import DinnerPartyDB

class DinnerParty:
    """Class to manage dinner party simulation."""
    def __init__(self):
        self.name = ""
        self.guests = []
        self.messages = []

        self.db = DinnerPartyDB()
        self.model = init_chat_model("gpt-4o", model_provider="openai")
        self.model_lite = init_chat_model("gpt-4o-mini", model_provider="openai")

    def __repr__(self) -> str:
        return f"DinnerParty(name={self.name}, guests={self.guests}, messages={self.messages})"

    def __str__(self) -> str:
        return f"DinnerParty(name={self.name}, guests={self.guests}, messages={self.messages})"

    def make_system_prompt(self) -> str:
        prompt = f"""You are simulating a dinner party with the following guests:
        {"\n".join([f"- {guest}" for guest in self.guests])}

        There is also an unnamed host, who will be referred to as Host.
        You will be shown a conversation in the following format:
        Host: <message>\n
        {self.guests[0]}: <message>\n
        {self.guests[1]}: <message>\n
        ...\n
        {self.guests[-1]}: <message>\n
        Host: <message>\n

        Your task is to generate a message as if you were one of the guests. Never respond as the host.
        Each guest is a famous personality. Use what you know about their personality to generate a message.
        If a specific guest is mentioned in the last message, respond only as that guest.
        If no specific guest is mentioned in the last message, respond as any one guest.
        Remember this is a dinner party, so keep the conversation lively and engaging, and involve all guests.

        Be sure your response matches the format of the conversation:
        <guest>: <message>\n"""
        return prompt

    def make_user_prompt_template(self, message: Optional[str] = None) -> str:
        conversation = "\n".join([message for message in self.messages])
        if message is not None:
            conversation += f"\nHost: {message}\n"
        conversation += "\n"
        return conversation

    def begin(self, name: Optional[str] = None, guests: Optional[List[str]] = None) -> None:
        """Create a new dinner party."""
        if name is not None:
            self.name = name
        else:
            self.name = input("What would you like to name your dinner party? ")
        if guests is not None:
            self.guests = guests
        else:
            self.guests = []
            while True:
                guest_name = input("Add a guest, entering one name at a time (or 'done' to finish): ")
                if guest_name.lower() == "done":
                    break
                is_famous = self.is_guest_famous(guest_name)
                if not is_famous:
                    print(f"{guest_name} is not a famous personality. Please try again.")
                    continue
                print(f"Adding {guest_name}")
                self.guests.append(guest_name)

    def save(self) -> str:
        """Save the dinner party to the database."""
        return self.db.parties.update_one(
            {"name": self.name},
            {"$set": {"guests": self.guests, "messages": self.messages}},
            upsert=True
        )

    def load(self, name: str) -> None:
        """Load a dinner party from the database."""
        party = self.db.parties.find_one({"name": name})
        if party is not None:
            self.name = party["name"]
            self.guests = party["guests"]
            self.messages = party.get("messages", [])
        else:
            raise ValueError(f"Dinner party '{name}' not found.")

    def is_guest_famous(self, guest: str) -> bool:
        """Check if a guest is famous."""
        prompt = f"""Is {guest} a famous personality? They can be real or fictional, but
        they should be someone you know enough about to reasonably impersonate.

        If {guest} is famous, return True. If {guest} is not famous, return False.
        """
        response = self.model_lite.invoke(prompt)
        return response.content == "True"


    def handle_turn(self, message: Optional[str] = None) -> None:
        """Handle a turn in the dinner party."""
        if message is not None:
            self.messages.append(f"Host: {message}")
        system_template: str = self.make_system_prompt()
        user_template: str = self.make_user_prompt_template(message)
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("user", user_template)
        ])
        prompt = prompt_template.invoke({})
        response = self.model.invoke(prompt)
        self.messages.append(response.content)
        print(response.content)
