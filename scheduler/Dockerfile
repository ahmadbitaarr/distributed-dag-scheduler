# Build context: repository root (docker build -f scheduler/Dockerfile .)
FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY protocol protocol
COPY scheduler scheduler
COPY artifact-store/pom.xml artifact-store/pom.xml
COPY worker/pom.xml worker/pom.xml
COPY client/pom.xml client/pom.xml
# Unit tests run in `mvn -B verify`; the image build only packages.
RUN mvn -B -q -pl scheduler -am package -DskipTests

FROM eclipse-temurin:21.0.5_11-jre-jammy
RUN useradd --system --no-create-home dag
WORKDIR /app
COPY --from=build /src/scheduler/target/scheduler-0.2.0.jar app.jar
USER dag
ENV PORT=8080 \
    ARTIFACT_BASE_URL=http://artifact-store:8081 \
    JAVA_OPTS="-Xms32m -Xmx128m -XX:ActiveProcessorCount=1"
EXPOSE 8080
HEALTHCHECK --interval=2s --timeout=2s --start-period=10s --retries=15 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/v1/health" || exit 1
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
