from dataclasses import asdict

import yaml
from pymongo import MongoClient

from mrf.plugins.data.domain_data import Context
from mrf.repositories.domain.data import RContext, \
    transform_context_for_database


def save_contexts(contexts: list[Context]):
    database = __setup_database()
    collection = database["context"]
    # TODO: Dataclass stuff here
    r_contexts: list[RContext] = []
    for c in contexts:
        r_contexts.append(transform_context_for_database(c))

    for c in r_contexts:
        context_dict = asdict(c)
        collection.insert_one(context_dict)


def __setup_database():
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
    db_config = config["database"]
    db_host = db_config["host"]
    db_port = db_config["port"]
    database_name = db_config["database_name"]
    mongo_uri = f"mongodb://{db_host}:{db_port}/"
    client = MongoClient(mongo_uri)
    return client[database_name]
