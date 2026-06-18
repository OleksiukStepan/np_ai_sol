FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY samples ./samples
COPY main.py .

# Input CSV and keys are mounted at runtime; outputs go to a mounted volume.
ENTRYPOINT ["python", "main.py"]
