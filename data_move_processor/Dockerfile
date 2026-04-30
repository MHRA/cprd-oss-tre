# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:4-python3.8-appservice as base
FROM mcr.microsoft.com/azure-functions/python:4-python3.10 as base
RUN apt-get update && apt-get install ca-certificates -y
COPY ZscalerRootCertificate-2048-SHA256.crt /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt
RUN /usr/sbin/update-ca-certificates
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt



FROM base as runtime

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    FUNCTIONS_WORKER_RUNTIME=python \
    PYTHON_ENABLE_WORKER_EXTENSIONS=1

WORKDIR /home/site/wwwroot

COPY . .

