import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

class DinnerPartyDB:
    '''
    DinnerPartyDB provides an interface to the learning-ai/dinnerParty collection in MongoDB Atlas.
    '''
    def __init__(self):
        _username = os.getenv("ATLAS_LEARNING_AI_USERNAME")
        _password = os.getenv("ATLAS_LEARNING_AI_PASSWORD")
        _mongodb_uri = f"mongodb+srv://{_username}:{_password}@learning-ai.rugqmov.mongodb.net/?retryWrites=true&w=majority&appName=learning-ai"
        self.client = MongoClient(_mongodb_uri, server_api=ServerApi('1'))
        self.database = self.client.get_database("dinnerParty")
        self.guests = self.database.get_collection("guests")

    def list_guests(self):
        for guest in self.guests.find():
            print()
            print(guest["name"])
            print()
            print(guest["personality"])
            print("====================================")

    def ping_mongodb(self):
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)