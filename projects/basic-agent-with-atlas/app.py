from dinner_party_db import DinnerPartyDB
from ai import SimpleAI


def simple_round_robin():
    question = input("What would you like to ask the guests? ")
    ai = SimpleAI()
    db = DinnerPartyDB()
    guests = db.guests.find()
    for guest in guests:
        response = ai.simple_question(guest["name"], guest["personality"], question)
        print()
        print(guest["name"])
        print()
        print(response.content)
        print()
        print("====================================")


if __name__ == "__main__":
    try:
        simple_round_robin()
    except Exception as e:
        print(e)
