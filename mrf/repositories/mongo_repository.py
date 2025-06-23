"""
Module for saving reconstructed information to a MongoDB based on specific
information.
"""

from dataclasses import asdict

import yaml
from pymongo import MongoClient

from modules.service import Microservice
from mrf.modules.domain_data import Context
from mrf.repositories.domain.data import RContext, transform_context_for_database
from repositories.service.service import RMicroservice, transform_microservice_for_database


def save_contexts(contexts: list[Context]):
    """
    Method for saving the reconstructed domain data information to a database.

    Args:
        contexts ([:class:`Context`]): List of reconstructed domain information.
    """
    database = __setup_database()
    collection_context = database["context"]
    r_contexts: list[RContext] = []
    for context in contexts:
        r_contexts.append(transform_context_for_database(context))

    for r_context in r_contexts:
        context_dict = asdict(r_context)
        collection_context.insert_one(context_dict)

def save_microservices(microservices: list[Microservice]):
    """
    Method for saving the reconstructed microservice information to a database.

    Args:
        microservices ([:class:`Microservice`]): List of reconstructed microservice information.
    """
    print("Microservice")
    database = __setup_database()
    collection_microservices = database["microservice"]
    r_microservices: list[RMicroservice] = []

    for microservice in microservices:
        r_microservices.append(transform_microservice_for_database(microservice))

    for r_microservice in r_microservices:
        microservice_dict = asdict(r_microservice)
        collection_microservices.insert_one(microservice_dict)



def __setup_database():
    with open("mrf/config.yaml", "r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    db_config = config["database"]
    db_host = db_config["host"]
    db_port = db_config["port"]
    database_name = db_config["database_name"]
    mongo_uri = f"mongodb://{db_host}:{db_port}/"
    client = MongoClient(mongo_uri)
    return client[database_name]
