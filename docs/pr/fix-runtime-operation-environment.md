## Summary

An operation node named the environment its image was **built** from, not the
one it **runs** on.

```diff
  FROM eclipse-temurin:21-jdk AS build      # scaffolding, discarded
  RUN ./mvnw -B package
  FROM eclipse-temurin:21-jre               # what actually runs
  ENTRYPOINT ["java", "-jar", "app.jar"]

- operation_environment = "eclipse-temurin:21-jdk"
+ operation_environment = "eclipse-temurin:21-jre"
```

`__base_image` returned the **first** `FROM`. In a multi-stage build the
earlier stages are build scaffolding and are discarded; only the final stage
becomes the running container.

The old comment shows the choice was deliberate — *"the first one is the
environment the build starts from"* — and it never showed, because every
Dockerfile here had both stages on the same image. Moving Lakeside Mutual off a
base image Docker Hub withdrew made the two differ, and the defect surfaced as
an unresolvable reference in the operation models.

It also resolves a stage alias. A final `FROM <earlier-stage>` names a **stage,
not an image**, so reading it literally would report something that is not an
image at all:

```text
FROM eclipse-temurin:21-jre AS base
FROM base                           → eclipse-temurin:21-jre, not "base"
```

## Evidence

**Before:** every Java container of Lakeside Mutual reported
`eclipse-temurin:21-jdk`, and the Eclipse editor said

```text
Couldn't resolve reference to OperationEnvironment 'eclipse-temurin:21-jdk'.
```

**After:** all of them report `eclipse-temurin:21-jre`, and the frontends report
`nginx:stable-alpine` rather than `node:16` — their build stage.

```console
$ uv run pytest -q
151 passed                       # was 150
$ uv run ruff check && uv run mypy
All checks passed!
Success: no issues found in 57 source files
```

`tests/fixtures/docker-multistage` is new because **`docker-minimal` cannot
catch this** — its Dockerfile is single-stage, so first and last agree. The new
fixture has two containers, each defeating a different wrong reading:

| Container | Dockerfile | Expected |
|---|---|---|
| `customer-core` | three stages, last a real image | `eclipse-temurin:21-jre` |
| `report-service` | final stage names the alias `base` | `eclipse-temurin:21-jre` |

**Both halves are mutation-tested.** Taking the first `FROM` fails one check;
not resolving the alias fails the other. The second container was added *after*
the first version of the fixture let that mutation pass — its aliased stage sat
in the middle, where resolution cannot change the answer.

`expected_pipeline.json` is written by hand. Its domain and service halves are
`docker-minimal`'s verbatim, since it is the same service; only the operation
environment differs, which is what the fixture exists to pin.

## Merge Danger

**Door:** two-way. One method.

**Blast Radius:** the `operation_environment` of every multi-stage container

**This needs its LEMMA counterpart.** An `OperationEnvironment` is an
enumerated reference, so a value the technology model does not declare cannot
resolve. `fix/temurin-operation-environments` in the LEMMA repository declares
the images this now reports. **Merging this alone reintroduces the very error it
fixes**, for the `-jre` image instead of the `-jdk` one.

Also worth knowing:

- **Any system with a multi-stage Dockerfile reports a different environment
  after this.** For Lakeside Mutual that is 5 Java containers and 3 frontends.
  A model reconstructed before this says the build image; regenerate rather than
  compare.
- **Nothing in the LEMMA regression test exercises it.** No expected folder
  contains operation models, which is why this reached the editor rather than a
  test. Verified instead by reconstructing Lakeside Mutual and cross-checking
  every `with operation environment` in the generated model against the
  declarations.
- `docker-minimal` is untouched and still passes, so the single-stage path is
  unchanged.

**The reconstruction has to be re-run** for the corrected values to reach the
database:

```console
! uv run mrf -r -p Java Spring Communication Docker Protobuf Node -t <system>
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
