Use the skill lemma-smell-refactoring:resolve-non-secured-communication.

## Finding

Security smell: Non-Secured Service-to-Service Communications
(Ponce et al. 2022, §3.7). Root cause 4 of 4 in this system, and the last
one left: the other three are already resolved in this tree.

The Risk Management server binds its gRPC endpoint without TLS, so it is
reached over plaintext by whatever is on the network with it.

## The facts, as the reconstructed LEMMA models state them

On RiskManagement:

    @javaWithSpring::_aspects.GrpcServer(host = "0.0.0.0", port = "50051",
        transportSecurity = "plaintext")

The models carry no file paths by design. Locate the code yourself.

No ServiceCall names this endpoint: the reconstruction found no microservice
of this system that calls it. Its caller is a component the deployment does
not contain, and it has to be secured in step regardless.

## Scope

This root cause only: the gRPC endpoint and whatever calls it. The Customer
Core's connector and the ActiveMQ broker are already mutually authenticated
in this tree - do NOT change them.

## Done when

- the gRPC server requires and verifies a client certificate
- whatever calls that endpoint presents one, from the same authority
- the Risk Management server still starts and still consumes its queue
