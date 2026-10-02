# Build context: repository root (docker build -f artifact-store/Dockerfile .)
FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY protocol protocol
COPY artifact-store artifact-store
COPY scheduler/pom.xml scheduler/pom.xml
COPY worker/pom.xml worker/pom.xml
COPY client/pom.xml client/pom.xml
# Unit tests run in `mvn -B verify`; the image build only packages.
RUN mvn -B -q -pl artifact-store -am package -DskipTests

FROM eclipse-temurin:21.0.5_11-jre-jammy
WORKDIR /app
COPY --from=build /src/artifact-store/target/artifact-store-0.2.0.jar app.jar
# Runs as root so it can write to a host bind mount at DATA_DIR regardless of host UID.
ENV PORT=8081 \
    DATA_DIR=/data \
    JAVA_OPTS="-Xms32m -Xmx128m -XX:ActiveProcessorCount=1"
VOLUME /data
EXPOSE 8081
HEALTHCHECK --interval=2s --timeout=2s --start-period=10s --retries=15 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/v1/health" || exit 1
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
