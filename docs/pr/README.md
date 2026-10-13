# Pull request bodies

One file per feature branch, named after it. Written when the branch was ready
and kept so the text survives the session it was written in.

They are a record of what a change claimed and what it was verified against, so
a later reader can check the claim rather than take it. The evidence sections
name the exact commands and their output.

The first three arrived with the branch `feat/communication-plugin`, which
contains the commits of the other two; the earlier branches are left alone so
their own diffs stay free of files describing themselves.

| File | Branch | Into |
|---|---|---|
| `feat-deployment-configuration.md` | `feat/deployment-configuration` | `dev` |
| `feat-rest-technology-information.md` | `feat/rest-technology-information` | `dev` |
| `feat-communication-plugin.md` | `feat/communication-plugin` | `dev` |
| `feat-service-dependencies.md` | `feat/service-dependencies` | `dev` |
| `feat-grpc-node-plugins.md` | `feat/grpc-node-plugins` | `dev` |
| `docs-plans-and-adr.md` | `docs/plans-and-adr` | `dev` |
| `docs-backlog.md` | `docs/backlog` | `dev` |
| `feat-server-endpoint-facts.md` | `feat/server-endpoint-facts` | `dev` |
| `docs-security-smells.md` | `docs/security-smells` | `dev` |
| `feat-async-communication.md` | `feat/async-communication` | `dev` |

Merge order matters for `docs/plans-and-adr`: it contains the commits of
`feat/rest-technology-information`, so that branch goes first. The rest are
independent of one another, except that `docs/security-smells` holds the plan
that `feat/async-communication` implements - either order merges, but reading
the plan first is what makes the implementation's decisions legible.
