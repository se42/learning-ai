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

One thing I'm wondering about this is that my guests are so famous, I'm not sure how useful these
personality profiles are. The model I'm giving them to surely knows who Socrates and Tyrion are without
the additional profile, and it can probably guess who the others are based on the profiles. For my
second pass, I think I will take advantage of this and focus on building conversational features with
known famous people. Then later, I can incorporate some purely fictional personas or maybe some personas
the models won't have easy access to.

## Second Pass

For the second pass, I plan to:

1. User can start a new dinner party with guests of their choosing, or continue a previous dinner party
2. The guests have to be famous people so I can rely on the model to impersonate them
    - Stretch: If the model doesn't know who the person is, the user can submit a profile describing them
3. Once the dinner party begins, the user can start the conversation or they can ask a guest to do so
4. The system will pause between each guest response, giving the user a chance to speak
5. The user can speak to the group or to a specific guest, or pass and let the guests continue
6. Guests will occasionally ask the user a question and wait for a response
7. If the user does not speak for ~10 turns, the guests will leave and the conversation will end
