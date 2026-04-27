FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

EXPOSE 5000

# The simulation engine keeps live state in process memory, so the container
# must run a single worker unless that state is moved to shared storage.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app:app"]
