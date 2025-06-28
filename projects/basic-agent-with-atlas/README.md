# Dinner Party with AI Agents

## First Pass

The first pass of this simple AI app went as follows:

1. I created a MongoDB Atlas cluster and added a database for my dinner party guests.
    - Socrates, Marcus Aurelius, Tyrion Lannister, Ruth Bader Ginsburg, Hannah Arendt, Søren Kierkegaard
    - I used ChatGPT-4o to generate the guest profiles and manually inserted them into the database.
2. I created a simple Python app that uses LangChain to query the guests and print their responses.
    - The first function, `simple_round_robin`, receives a question from the user and asks each guest in turn for their response.
    - There is no conversation memory and no interaction between guests.

The [personalities](first-pass/guests.txt) used and a few of their responses are in the `first-pass` directory.
    