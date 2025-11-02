FROM python:3.11-slim

WORKDIR /app

# Copy base template infrastructure
COPY base-bot-template/ /app/base/

# Copy our strategy template
COPY momentum-reversion-template/ /app/strategy/

# Install dependencies
COPY base-bot-template/requirements.txt /app/base/requirements.txt
RUN pip install --no-cache-dir -r /app/base/requirements.txt

# Set working directory to strategy
WORKDIR /app/strategy

# Run the bot
CMD ["python", "startup.py"]
