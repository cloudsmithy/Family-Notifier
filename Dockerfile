# ---- Base Stage ----
FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies required for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---- Builder Stage ----
FROM base as builder

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Final Stage ----
FROM base

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Set the PATH to include the user's local bin directory
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY ./family_notifier /app/family_notifier

# Set non-root user for security
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

# Expose the port Gunicorn will run on
EXPOSE 5001

# Run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "family_notifier.app:app"]
