FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY scenarios ./scenarios

RUN pip install --no-cache-dir .

# Default to running the bundled scenarios and emitting both reports.
ENTRYPOINT ["hilbench"]
CMD ["scenarios/", "--json", "report.json", "--junit", "report.xml"]
