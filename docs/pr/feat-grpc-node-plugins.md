## Summary

Lakeside Mutual has one component that is not written in Java, and MRF saw
nothing of it: the Docker plugin found `risk-management-server`'s container and
the other phases found nothing to put in it, so it sat in the operation model's
skipped list and nowhere else. Steps 1 and 2 of `docs/node-plugin-plan.md`, which
is the first commit here.

```diff
 contexts        4 -> 5        + RiskManagement
 microservices   4 -> 5        + riskmanagement.RiskManagement
 skipped nodes   4 -> 3        RiskManagementServerContainer now deploys a service
```

```
context RiskManagement {                               # from riskmanagement.proto
    structure TriggerReply { Report report, int progress }
    structure Report { string csv }
}

public functional microservice riskmanagement.RiskManagement {
    interface RiskManagement {
        Trigger(sync in triggerRequest : …, sync out triggerReply : …);
    }
}
```

**A proto file is a better contract than an annotated Java class** — it names the
service, its operations, their types and the structures those types are, in one
place — and it maps onto the existing concepts with **no model extension**:
`service` → microservice, `rpc` → operation with two typed parameters, `message`
→ structure, `enum` → enumeration, `repeated` → collection, `stream` →
asynchronous.

**The parser is hand-written.** `protobuf` parses no `.proto` source at all and
`grpcio-tools` ships the whole of `protoc`, while the grammar for these
declarations is small and closed. Options, imports, reserved ranges and field
options are read and skipped so a file that uses them parses rather than failing;
comments are removed before anything is read, so a commented-out declaration
never reaches the model.

**The Node plugin reconstructs no microservice of its own**, which is what keeps
the frontends out: a `package.json` says something is a Node project, not a
service, and all three frontends have one — two even configure an address. It
attaches to what the Protobuf plugin produced:

```
GrpcServer    {host: 0.0.0.0, port: 50051, transportSecurity: UNRESOLVED}
MessageQueue  {host: localhost, port: 61613, broker: activemq,
               queue: newpolicies, scheme: stomp,
               credentialsConfigured: true, transportSecurity: UNRESOLVED}
```

The `MessageQueue` fact is the consumer side of a link already reconstructed:
`policy-management-backend` produces to `riskmanagement.queueName=newpolicies`.

## Evidence

### Four correctness problems the work turned up

**A nested message carried a dot into the model.** `Order.OrderLine` qualified as
`…OrderQuery.Order.OrderLine` makes the LEMMA side read the context as `Order`,
because it takes the second-to-last part of a structure's qualified name — and a
structure's name is a single identifier there anyway. Nested names join with an
underscore now, and a reference by either the simple or the qualified name
resolves to it, with an ambiguous simple name left unresolved rather than pointed
at one of them. **Found only because a test asserts that rule directly**; no
comparison of reconstructed output would have noticed.

**A type of an imported file claimed a structure.**
`google.protobuf.Timestamp` is `UNSPECIFIED` now, as the Spring plugin treats a
framework type.

**A field referring to an enumeration said `DATA_STRUCTURE`**, so the generator
would have referenced a structure that was never declared.

**The gRPC address stated the wrong protocol.** Reported as `Endpoint`, it was
generated as `@endpoints(javaWithSpring::_protocols.rest: …)` — a gRPC service
reached over REST. Verified by generating the models, then changed to a name of
its own; the model now says nothing about the protocol rather than something
false.

### Step 2 fixes what step 1 broke

With a microservice to deploy, `RiskManagementServerContainer` stopped being
skipped — and the strict `deployment_base.technology` marks
`springApplicationName` and `serverPort` mandatory of every container that
deploys one, which a Node service has not got. The generated model faulted on
that container. The Docker plugin now falls back to `package.json` and
`config.json`:

```
container RiskManagementServerContainer
    with operation environment "node:16"
    deploys RiskManagement::riskmanagement.RiskManagement
    default values {
        springApplicationName = "risk-management"
        serverPort = 50051
    }
```

All six deploying containers carry their values, so the mandatory check returns
early for each. **This is why the two steps are one pull request**: step 1 alone
leaves `dev` generating an operation model the Operation DSL rejects.

### Three things deliberately not claimed

- `transportSecurity: UNRESOLVED`, not `plaintext` — whether a channel is
  encrypted is decided in the JavaScript that opens it, which this step does not
  read, and absence of a TLS section is not evidence.
- **A credential is never reported**, only that one is configured. A test asserts
  that neither `secret` nor `queueuser` reaches the model.
- A configuration shape the constants do not name yields nothing; the file is a
  convention of the service rather than of Node.

```text
ruff    All checks passed!
mypy    Success: no issues found in 54 source files
pytest  121 passed          # 83 before
```

Three fixtures, 22 unit tests on the parser, and golden tests that assert the
qualified-name and microservice-name rules themselves. Generated end to end
against the live database: 5 contexts, 5 microservices, 11 models, the operation
model's diff against the previous run being exactly the new container and its
import.

## Merge Danger

**Door:** two-way. Both plugins only run when selected; nothing existing changes
unless `Protobuf` or `Node` is passed, which is asserted rather than assumed.

**Blast Radius:** systems with a `.proto` file

`mrf/utilities/sping.py` gives up its two endpoint constants to
`mrf/utilities/meta_data.py` and re-exports them, so the names a plugin imports
are unchanged — a protobuf plugin importing from a module named after Spring was
the alternative.

The Docker plugin's configuration reading gained a fallback. It is reached only
when a build directory holds no `application.properties`, so no Spring service is
affected.

`GrpcServer` and `MessageQueue` do not appear in the generated models:
`spring.technology` declares no such aspects, so the generator filters them out
as it filters any undeclared name. The facts are in the database for whatever
reads them next.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
