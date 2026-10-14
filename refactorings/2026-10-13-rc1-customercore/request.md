Use the skill lemma-smell-refactoring:resolve-non-secured-communication.

## Finding

Security smell: Non-Secured Service-to-Service Communications
(Ponce et al. 2022, §3.7). Root cause 1 of 2 in this system.

CustomerCore answers on a single plaintext connector. Three services call it,
and all three calls are therefore unprotected. This one root cause accounts
for 3 of the system's 9 findings.

## The facts, as the reconstructed LEMMA models state them

On CustomerCore:

    @javaWithSpring::_aspects.ServerEndpoint(connector = "server",
        port = "8110", ^protocol = "http", tlsEnabled = false)

On CustomerManagement:

    @javaWithSpring::_aspects.ServiceCall(target = "CustomerCore",
        targetKind = "SERVICE", scheme = "http", ^technology = "Feign")

On CustomerSelfService:

    @javaWithSpring::_aspects.ServiceCall(target = "CustomerCore",
        targetKind = "SERVICE", scheme = "http", ^technology = "RestTemplate")

On PolicyManagement:

    @javaWithSpring::_aspects.ServiceCall(target = "CustomerCore",
        targetKind = "SERVICE", scheme = "http", ^technology = "RestTemplate")

The models carry no file paths by design. Locate the code yourself.

## Scope

This root cause only: CustomerCore's connector and the three callers above.
Do NOT refactor the ActiveMQ broker or any message queue - that is root
cause 2 and is handled separately.

## Done when

- CustomerCore reconstructs with tlsEnabled = true and client authentication
  required
- all three callers reconstruct with scheme = "https"
- every affected service still compiles with its own ./mvnw
