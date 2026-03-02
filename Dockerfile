# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies into a virtualenv (or system-wide since it's a container)
# To keep it simple, we just install to the system in the container
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r qcm_group && useradd -r -g qcm_group qcm_user

WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy the application code
COPY . .

# Ensure instance directory exists and has correct permissions
RUN mkdir -p /app/instance && chown -R qcm_user:qcm_group /app

# Expose port
EXPOSE 5000

# Switch to non-root user
USER qcm_user

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
