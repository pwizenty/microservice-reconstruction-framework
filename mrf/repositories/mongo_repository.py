"""Persistence of reconstructed architecture information in MongoDB."""

from dataclasses import asdict
from typing import Any

import yaml
from pymongo import MongoClient

from mrf.modules.domain_data import Context
from mrf.modules.operation import OperationNode
from mrf.modules.service import Microservice
from mrf.repositories.domain.data import RContext, transform_context_for_database
from mrf.repositories.operation.operation import (
    ROperationNode,
    transform_operation_node_for_database,
)
from mrf.repositories.service.service import (
    RMicroservice,
    transform_microservice_for_database,
)


def save_contexts(contexts: list[Context], replace: bool = False):
    """Method for saving the reconstructed domain data information to a database.

    Args:
        contexts ([:class:`Context`]): List of reconstructed domain information.
        replace (bool): Drop the documents of earlier runs before saving.
    """
    database = __setup_database()
    collection_context = database["context"]
    r_contexts: list[RContext] = []
    for context in contexts:
        r_contexts.append(transform_context_for_database(context))

    __save(collection_context, [asdict(r) for r in r_contexts], replace)


def save_microservices(microservices: list[Microservice], replace: bool = False):
    """Method for saving the reconstructed microservice information to a database.

    Args:
        microservices ([:class:`Microservice`]): List of reconstructed
            microservice information.
        replace (bool): Drop the documents of earlier runs before saving.
    """
    database = __setup_database()
    collection_microservices = database["microservice"]
    r_microservices: list[RMicroservice] = []

    for microservice in microservices:
        r_microservices.append(transform_microservice_for_database(microservice))

    __save(collection_microservices, [asdict(r) for r in r_microservices], replace)


def save_operation_nodes(nodes: list[OperationNode], replace: bool = False):
    """Method for saving the reconstructed operation information to a database.

    Args:
        nodes ([:class:`OperationNode`]): List of reconstructed operation
            information.
        replace (bool): Drop the documents of earlier runs before saving.
    """
    database = __setup_database()
    collection_operation = database["operation"]
    r_nodes: list[ROperationNode] = []

    for node in nodes:
        r_nodes.append(transform_operation_node_for_database(node))

    __save(collection_operation, [asdict(r) for r in r_nodes], replace)


def __save(collection, documents: list[dict[str, Any]], replace: bool):
    """Write the documents of one reconstruction run into a collection.

    A document is identified by its qualified name, so running the
    reconstruction again updates what it found before instead of adding a
    second copy of it. Without that, every run doubled the elements a
    consumer sees, and the wizard of LEMMA offered the same context twice
    with no way to tell the current one from the stale one.

    An element of an earlier run that the current one did not find is left
    untouched, which is what allows several systems to share a database.
    ``replace`` drops the collection's documents first, for the case where
    the run is meant to be the whole content of the database.

    Args:
        collection: Collection to write to
        documents ([dict]): Documents of the current run
        replace (bool): Drop the documents of earlier runs before saving
    """
    if replace:
        collection.delete_many({})

    for document in documents:
        collection.replace_one(
            {"qualified_name": document["qualified_name"]}, document, upsert=True
        )


def __setup_database():
    with open("mrf/config.yaml", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    db_config = config["database"]
    db_host = db_config["host"]
    db_port = db_config["port"]
    database_name = db_config["database_name"]
    mongo_uri = f"mongodb://{db_host}:{db_port}/"
    client: MongoClient[dict[str, Any]] = MongoClient(mongo_uri)
    return client[database_name]
