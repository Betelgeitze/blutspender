FROM python:3.10

WORKDIR /blutspender
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . ./app
CMD ["python", "./app/main.py"]