FROM python:3.11-slim  
  
WORKDIR /app  
  
# Install dependencies  
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt  
  
# Copy code  
COPY . .  
  
# Set environment variables  
ENV PYTHONUNBUFFERED=1  
ENV PYTHONPATH=/app  
  
# Run health check by default  
CMD ["python", "-m", "backend.health_check"] 
