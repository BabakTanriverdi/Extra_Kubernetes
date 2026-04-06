FROM python:3.11-alpine
WORKDIR /app
RUN pip install flask
COPY myshop.py .
EXPOSE 80
CMD ["python", "myshop.py"]