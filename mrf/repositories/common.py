"""Module with common elements for database persistance."""

from dataclasses import dataclass, field

from mrf.plugins.common.common_plugin import Data


@dataclass
class RData:
    """Persistence representation of :class:`Data`.

    Integrates meta-data into the reconstructed information.

    Attributes:
        name (str): Name of the meta-data information
        values (dict): Key-Value information about the meta-data information
    """

    name: str
    values: dict[str, str] = field(default_factory=dict)


def to_rdata(data: Data) -> RData:
    """Convert :class:`Data` meta-data into its persistence representation.

    Args:
        data (Data): Reconstructed meta-data information.

    Returns:
        RData: Persistence representation of the meta-data.
    """
    r_data = RData(data.name)
    r_data.values = data.values
    return r_data
