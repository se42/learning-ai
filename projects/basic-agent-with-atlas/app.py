"""Dinner Party Guest Simulator.

This module provides a command-line interface for simulating conversations with AI-powered
dinner party guests based on famous personalities.
"""

from typing import List, Optional, Tuple

from dinner_party_db import DinnerPartyDB
from ai import SimpleAI


def simple_round_robin(guests: List[str]) -> None:
    """Conduct a round-robin Q&A session with all dinner party guests.

    Prompts the user for a question, then collects and displays responses from each guest.
    Responses are formatted with the guest's name and separated by visual dividers.

    Args:
        guests: List of guest names to participate in the Q&A.
    """
    question: str = input("What would you like to ask the guests? ")
    ai: SimpleAI = SimpleAI()
    for guest in guests:
        personality = f"Your personality is that of the famous character {guest}."
        response = ai.simple_question(guest, personality, question)
        print(f"\n{guest}\n\n{response.content}\n\n{'=' * 36}")

def party() -> None:
    """Orchestrate the dinner party simulation.
    
    Handles the main party flow including:
    - Creating new parties or resuming existing ones
    - Managing guest lists
    - Initiating conversation rounds
    """
    db: DinnerPartyDB = DinnerPartyDB()
    if db.parties.count_documents({}) == 0:
        print("No dinner parties found. Let's create one!")
        party_name, guests = create_new_party(db)
    else:
        parties = list(db.parties.find(projection={"_id": 0, "name": 1, "guests": 1}))
        for i, party in enumerate(parties):
            print(f"{i + 1}. {party['name']} -- {', '.join(party['guests'])}")
        party_number: str = input("Which dinner party would you like to resume? Enter 'new' to create a new one. ")
        if party_number == "new":
            party_name, guests = create_new_party(db)
        else:
            party = parties[int(party_number) - 1]
            party_name = party['name']
            guests = party['guests']
            print(f"Great! Let the party begin! Resuming dinner party \"{party_name}\" with guests: {guests}")
    simple_round_robin(guests)

def create_new_party(db: DinnerPartyDB) -> Tuple[str, List[str]]:
    """Create a new dinner party and add it to the database.
    
    Args:
        db: Database connection for storing party information.
        
    Returns:
        A tuple containing the party name and list of guest names.
    """
    party_name: str = input("What would you like to name your dinner party? ")
    guests: List[str] = []
    guest_name: str = input("Who would you like to invite to your dinner party? Enter one name at a time. ")
    guests.append(guest_name)
    while True:
        guest_name = input("Who else would you like to invite? (or 'done' to finish) ")
        if guest_name.lower() == "done":
            break
        guests.append(guest_name)
    db.create_party(party_name, guests)
    print(f"Created dinner party '{party_name}' with guests: {', '.join(guests)}")
    return party_name, guests
    
def main() -> None:
    """Entry point for the Dinner Party Guest Simulator.
    
    Handles the application startup and manages any unhandled exceptions.
    """
    try:
        party()
    except KeyboardInterrupt:
        print("\nGoodbye! Thanks for hosting a dinner party!")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise


if __name__ == "__main__":
    main()
