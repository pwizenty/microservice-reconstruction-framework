"""
Module with common elements for database persistance.
"""

from dataclasses import dataclass

from plugins.common.common_plugin import Data


@dataclass
class RData:
    """
    Data structure class for the integration of meta-data into reconstructed
    information.

    Attributes:
        name (str): Name of the meta-data information
        values (dict): Key-Value information about the meta-data information
    """

    name: str
    values = {}

def to_rdata(data: Data):
    r_data = RData(data.name)
    r_data.values = data.values
    return r_data