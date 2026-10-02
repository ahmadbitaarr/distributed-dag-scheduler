# Build context: repository root (docker build -f worker/Dockerfile .)
FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY protocol protocol
COPY worker worker
COPY scheduler/pom.xml scheduler/pom.xml
COPY artifact-store/pom.xml artifact-store/pom.xml
COPY client/pom.xml client/pom.xml
# Unit tests run in `mvn -B verify`; the image build only packages.
RUN mvn -B -q -pl worker -am package -DskipTests

FROM eclipse-temurin:21.0.5_11-jre-jammy
# The worker invokes ffmpeg/ffprobe for inspect, transcode and thumbnail operations.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --no-create-home dag
WORKDIR /app
COPY --from=build /src/worker/target/worker-0.2.0.jar app.jar
USER dag
ENV SCHEDULER_URL=http://scheduler:8080 \
    ARTIFACT_BASE_URL=http://artifact-store:8081 \
    POLL_INTERVAL_MS=100 \
    OPERATION_TIMEOUT_MS=30000 \
    JAVA_OPTS="-Xms32m -Xmx128m -XX:ActiveProcessorCount=1"
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
