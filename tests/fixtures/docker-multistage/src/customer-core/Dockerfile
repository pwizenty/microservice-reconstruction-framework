FROM eclipse-temurin:21-jdk AS build
COPY . .
RUN ./mvnw -B package

FROM build AS verify
RUN ./mvnw -B verify

FROM eclipse-temurin:21-jre
COPY --from=build target/customer-core.jar /app.jar
ENTRYPOINT ["java", "-jar", "/app.jar"]
