"""Meta-data names the reconstruction shares across technologies.

A name here is read by the LEMMA side, so it belongs to no single technology:
the Spring plugin reports the path of a controller under it and the Protobuf
plugin the qualified name of a gRPC service, and the generator turns either into
an endpoint of the model.
"""

ENDPOINT = "Endpoint"
"""Meta-data name of the address an element answers under.

An address is relative to the element above it - a path on an operation is read
below the path of its interface - which is how Spring and LEMMA both read one.
"""

ENDPOINT_ADDRESS = "address"
"""Key under which an :data:`ENDPOINT` holds its address."""
