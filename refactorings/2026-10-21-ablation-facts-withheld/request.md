Use the skill lemma-smell-refactoring:resolve-non-secured-communication.

## Finding

Security smell: Non-Secured Service-to-Service Communications
(Ponce et al. 2022, §3.7). Root cause 1 of 2 in this system.

The CustomerCore service answers on a connector that does not protect the
channel, and the services that call it are therefore unprotected as well.

## The facts

Deliberately not given. Read the sources: which connector CustomerCore
answers on, which services call it, and with which client each of them
calls, are for you to establish.

## Scope

This root cause only: CustomerCore's connector and its callers. Do NOT
refactor the ActiveMQ broker or any message queue - that is root cause 2
and is handled separately.

## Done when

- CustomerCore requires TLS with client authentication on the connector its
  callers use
- every caller of CustomerCore uses TLS and presents a client certificate
- every affected service still compiles with its own ./mvnw test
