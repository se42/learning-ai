from dinner_party_db import DinnerPartyDB
from ai import SimpleAI


def simple_round_robin() -> None:
    """Prompt the user for a question and generate AI responses for each dinner party guest.

    Iterates through all guests in the database, asks the AI to respond as each guest,
    and prints the results in a readable format.
    """
    question: str = input("What would you like to ask the guests? ")
    ai: SimpleAI = SimpleAI()
    db: DinnerPartyDB = DinnerPartyDB()
    guests = db.guests.find()
    for guest in guests:
        response = ai.simple_question(guest["name"], guest["personality"], question)
        print(f"\n{guest['name']}\n\n{response.content}\n\n{'=' * 36}")


def main() -> None:
    """Main entry point for the application."""
    try:
        simple_round_robin()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
