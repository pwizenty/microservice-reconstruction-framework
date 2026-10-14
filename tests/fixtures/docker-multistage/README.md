# docker-multistage

A single Spring service whose Dockerfile has **three** stages, so that the
first `FROM`, the last `FROM` and an intermediate stage built from an alias are
all different images:

```dockerfile
FROM eclipse-temurin:21-jdk AS build      # build scaffolding, discarded
FROM build AS verify                      # names a STAGE, not an image
FROM eclipse-temurin:21-jre               # what actually runs
```

The container runs on `eclipse-temurin:21-jre`. Reading the **first** `FROM`
would report `…-jdk`, and resolving the alias naively would report `build`,
which is not an image at all — so each wrong reading gives a distinct wrong
answer rather than coincidentally the right one.

`docker-minimal` cannot catch this: its Dockerfile is single-stage, so first
and last agree. Lakeside Mutual's were effectively the same until its base
image was withdrawn from Docker Hub and the build and runtime stages stopped
being identical, which is what exposed the defect.

Origin: hand-written for this test, modelled on `docker-minimal`. No upstream
licence applies.
