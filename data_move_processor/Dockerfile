FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Trust Zscaler cert
RUN apt-get update && apt-get install -y ca-certificates
COPY ZscalerRootCertificate-2048-SHA256.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    FUNCTIONS_WORKER_RUNTIME=python


WORKDIR /home/site/wwwroot


COPY host.json ./host.json

COPY app.py ./app.py
COPY function_app.py ./function_app.py


COPY durable_app.py ./durable_app.py


COPY activities ./activities
COPY orchestrators ./orchestrators
COPY shared ./shared
COPY requirements.txt ./requirements.txt


RUN pip install --no-cache-dir -r requirements.txt

