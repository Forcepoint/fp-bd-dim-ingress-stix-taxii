FROM python:3.8-alpine
RUN apk add --no-cache libffi-dev gcc musl-dev make && pip3 install --upgrade pip
WORKDIR /app
COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt
CMD ["python", "./main.py"]
