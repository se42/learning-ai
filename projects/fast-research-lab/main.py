import logging

from fastapi import FastAPI, Query
from pydantic import BaseModel
from beanie import Document, init_beanie
from typing import Annotated

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI()

class Message(BaseModel):
    author: str # Literal['user', 'researcher', 'idiot', 'flower_child']
    message: str

class UserMessage(Message):
    author: str | None = 'user'

class Topic(Document):
    subject: str
    prompt: str
    status: str
    messages: list[Message]


@app.get("/")
async def read_root():
    return 'Welcome to the Fast Research Lab!'

@app.post("/topics")
def create_topic(topic: Topic) -> Topic:
    logger.info(f"Creating topic: {topic}")
    logger.info("Starting agents for topic: {topic.subject}")
    return topic

@app.get("/topics/{topic_id}")
def get_topic(topic_id: str, turns: Annotated[int | None, Query(ge=0)] = None) -> Topic:
    topic = Topic.find_one({"_id": topic_id})
    if turns is not None:
        topic.messages = topic.messages[-turns:]
    return topic

@app.post("/topics/{topic_id}")
def add_message(topic_id: str, message: UserMessage) -> Topic:
    topic = Topic.find_one({"_id": topic_id})
    topic.messages.append(message)
    topic.save()
    logger.info(f"Added message: {message}")
    logger.info(f"Starting agents for topic: {topic.subject}")
    return topic
