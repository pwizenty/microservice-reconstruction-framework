---
name: resolve-non-secured-communication
description: Apply the refactoring "Use Mutual TLS" to a non-secured channel between two microservices - security smell §3.7 of Ponce et al. (2022). Use when LEMMA's smell detection reports Non-Secured Service-to-Service Communications and a patch resolving it is wanted.
---

# Resolve non-secured service-to-service communication

## What you are resolving

Two microservices of one application interact over a channel that protects
neither confidentiality, integrity nor authenticity. Ponce et al. (2022),
*Smells and refactorings for microservices security*, JSS 192:111393, §3.7 -
the smell holds **even if the two services are within the same network**, which
is why a plaintext call between two containers on one Docker network is a
finding and not an acceptable shortcut.

The refactoring the paper prescribes is **Use Mutual TLS**: mutual rather than
plain TLS, because it also authenticates the peers.

## What you are given

The finding, and the facts as the reconstructed LEMMA model states them - the
`ServiceCall`, `ServerEndpoint` and `MessageChannel` aspect lines. Those name
the services, the scheme, the queue and the broker. They deliberately carry
**no file paths**, so locate the code yourself from the service names.

You are given one **root cause**, not one channel: a server's connector plus
every client that calls it, or a broker plus every client that uses it. Fix all
of it. Mutual TLS needs both ends - a server with TLS and clients still on
plaintext is a broken system, not a refactored one.

## Procedure

1. **Map the root cause to files.** Find the server's or broker's configuration,
   then every client that addresses it. Clients are usually found by the
   property that holds the address, not by the service name.
2. **Read the matching recipe** in `references/`, by technology.
3. **Generate development certificates** - `references/certificates.md`. Commit
   the generating script, never the generated key material.
4. **Change both ends**, server/broker first, then every client.
5. **Compile** each affected service with its own `./mvnw` (each microservice
   has one), or the equivalent for a non-Java service.

## Recipes

| Channel | Recipe |
|---|---|
| Spring REST, server and clients | `references/spring-rest.md` |
| ActiveMQ over OpenWire, from Java | `references/activemq-openwire.md` |
| ActiveMQ over STOMP, from Node | `references/activemq-stomp.md` |
| Key and trust stores | `references/certificates.md` |

## Definition of done

Stated in the recognition rules of the Microservice Reconstruction Framework,
because the patch is verified by re-reconstructing the system and re-running
detection. If MRF cannot read the change, the refactoring cannot be shown to
have worked - however correct it is.

**For a server and its callers:**
- every `ServerEndpoint` reconstructs with `tlsEnabled = true`
- and with `clientAuth` set to require a client certificate
- every `ServiceCall` to it reconstructs with `scheme = "https"`

**For a broker and its clients:**
- the broker's connector scheme is `ssl` or `stomp+ssl`
- **no plaintext connector remains** (see pitfalls)
- every client's broker address uses the TLS scheme

## Pitfalls

These are specific to this toolchain and this smell. Each one has produced a
patch that looked right and was not.

- **The least protected connector wins.** MRF reports the transport of the
  *least* protected connector a broker offers. Adding an `ssl://` connector
  beside an existing `tcp://` one changes nothing: the broker still accepts
  plaintext, so it is still a finding. The plaintext connector must be removed
  or converted, not supplemented.
- **A broker may have more than one plaintext connector.** Check every
  `addConnector` call and every bind-address property. Converting one and
  leaving another is the same failure as above.
- **TLS without client authentication is not mutual TLS.** It secures the
  channel but does not authenticate the peers, which is a weaker refactoring
  than §3.7 cites. Configure client authentication as required, on both ends.
- **A client's address may be the server's own bind-address property.** Do not
  assume `spring.activemq.broker-url`; a client may reach a broker through a
  property that reads like server configuration.
- **Test configuration is not test code.** Updating a test's properties so it
  addresses the new transport is part of the refactoring. Disabling a test,
  weakening an assertion, or turning off certificate verification to make
  something pass is not - and `TrustAllStrategy`, `NoopHostnameVerifier` or
  `InsecureTrustManagerFactory` would each introduce a different smell.

## Never

- Never edit a `.services`, `.data` or `.operation` file. They are reconstructed
  output, not input: changing one makes the model contradict the system it
  describes, and it is overwritten on the next reconstruction anyway.
- Never resolve this by Kubernetes manifests or a service mesh. A mesh may well
  be the better answer in production, but MRF does not read manifests, so the
  result would be unverifiable here.
- Never weaken verification to make a connection succeed.
