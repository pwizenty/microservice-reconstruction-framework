FROM eclipse-temurin:21-jre AS base
COPY target/report-service.jar /app.jar

FROM base
ENTRYPOINT ["java", "-jar", "/app.jar"]
