import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

class DinnerPartyDB:
    """Provides an interface to the learning-ai/dinnerParty collection in MongoDB Atlas."""

    def __init__(self) -> None:
        """Initialize the MongoDB client and connect to the dinnerParty database."""
        _username: str | None = os.getenv("ATLAS_LEARNING_AI_USERNAME")
        _password: str | None = os.getenv("ATLAS_LEARNING_AI_PASSWORD")
        _mongodb_uri: str = (
            f"mongodb+srv://{_username}:{_password}@learning-ai.rugqmov.mongodb.net/"
            "?retryWrites=true&w=majority&appName=learning-ai"
        )
        self.client: MongoClient = MongoClient(_mongodb_uri, server_api=ServerApi('1'))
        self.database = self.client.get_database("dinnerParty")
        self.guests = self.database.get_collection("guests")

    def list_guests(self) -> None:
        """Print the name and personality of each guest in the collection."""
        for guest in self.guests.find():
            print(f"\n{guest['name']}\n\n{guest['personality']}\n{'=' * 36}")

    def ping_mongodb(self) -> None:
        """Ping MongoDB to confirm a successful connection."""
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)

    def close(self) -> None:
        """Close the MongoDB client connection."""
        self.client.close()