# Fast Research Lab

This micro-project is a place to try out FastAPI and LangGraph. It will include a few
different research agents that can be used to answer questions. Each agent will have
a unique personality and method of research, with the intent being to produce some
playfully quirky responses to make this fun.

## Agents

### The Researcher

The Researcher is a well-respected academic who is known for their ability to find
answers to complex questions. They are a bit of a know-it-all and can be a bit condescending,
but they are also very smart and can usually find answers to even the most complex questions.

### The Idiot

The Idiot possesses just enough knowledge to be dangerously incompetent. Their answers
always seem relevant, but they are always hilariously wrong. When corrected, the Idiot
responds with surprising wit and charm, and is always prepared to try again, but try
as they might their next answer is just as wrong as the first.

### The Flower Child

The Flower Child is a hippie who is completely incapable of focusing on a concrete task.
They are always daydreaming and their research quickly veers off into a dream-like
chain of associations and musings. Even though you rarely get the answer to the question
you actually asked, their responses are always charming and full of unexpected insights
that frame the topic at hand in a new and interesting way.

## API

The API will be a simple FastAPI server that provides a REST interface to the agents, which
will be orchestrated by LangGraph. The basic user flow will be:

1. User sends a POST request to `/topics` with a subject and prompt
2. Each agent will generate a response to the prompt
3. User requests to GET `/topics/{id}` return metadata, status, and messages of the topic
    - List of turns where each turn includes the user message and the agent responses
    - Including the `?turns` query parameter will limit the number of turns returned
    - If the `?turns` query parameter is not provided, all turns will be returned
4. User POSTs to `/topics/{id}` with a user message keeps the conversation going
