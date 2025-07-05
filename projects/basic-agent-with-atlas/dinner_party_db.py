"""MongoDB interface for managing dinner party data.

This module provides a DinnerPartyDB class to interact with MongoDB Atlas
for storing and retrieving dinner party information.
"""

import os
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

class DinnerPartyDB:
    """Interface for interacting with the dinner party database in MongoDB Atlas.

    This class provides methods to manage dinner parties and their guests,
    including creating parties, listing guests, and testing database connections.
    """

    def __init__(self) -> None:
        """Initialize MongoDB client and connect to the dinnerParty database.

        Raises:
            pymongo.errors.ConfigurationError: If MongoDB connection fails.
        """
        _username: str | None = os.getenv("ATLAS_LEARNING_AI_USERNAME")
        _password: str | None = os.getenv("ATLAS_LEARNING_AI_PASSWORD")
        _mongodb_uri: str = (
            f"mongodb+srv://{_username}:{_password}@learning-ai.rugqmov.mongodb.net/"
            "?retryWrites=true&w=majority&appName=learning-ai"
        )
        self.client: MongoClient = MongoClient(_mongodb_uri, server_api=ServerApi('1'))
        self.database: Database = self.client.get_database("dinnerParty")
        self.guests: Collection = self.database.get_collection("guests")
        self.parties: Collection = self.database.get_collection("parties")

        self.parties.create_index([("name", 1)], unique=True)

    def list_guests(self) -> None:
        """List all guests in the database with their personalities.
        
        Prints each guest's name and personality in a formatted way.
        """
        for guest in self.guests.find():
            print(f"\n{guest['name']}\n\n{guest['personality']}\n{'=' * 36}")
    
    def create_party(self, name: str, guests: List[str]) -> str:
        """Create a new dinner party in the database.

        Args:
            name: The name of the dinner party.
            guests: List of guest names to invite to the party.

        Returns:
            str: The ID of the newly created party document.
        """
        party = self.parties.insert_one({"name": name, "guests": guests})
        return str(party.inserted_id)

    def ping_mongodb(self) -> bool:
        """Test the MongoDB connection.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB!")
            return True
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            return False

    def close(self) -> None:
        """Close the MongoDB client connection.
        
        This should be called when the database connection is no longer needed.
        """
        self.client.close()