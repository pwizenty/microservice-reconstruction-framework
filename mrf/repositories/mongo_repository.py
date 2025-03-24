"""
Module for saving reconstructed information to a MongoDB based on specific
information.
"""

from dataclasses import asdict

import yaml
from pymongo import MongoClient

from mrf.modules.domain_data import Context
from mrf.repositories.domain.data import RContext, transform_context_for_database


def save_contexts(contexts: list[Context]):
    """
    Method for saving the reconstructed domain data information to a database.

    Args:
        contexts ([:class:`Context`]): List of reconstructed domain information.
    """
    database = __setup_database()
    collection = database["context"]
    r_contexts: list[RContext] = []
    for c in contexts:
        r_contexts.append(transform_context_for_database(c))

    for c in r_contexts:
        context_dict = asdict(c)
        collection.insert_one(context_dict)


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
