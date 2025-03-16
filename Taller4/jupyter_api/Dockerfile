FROM python:3.9
ARG AWS_ACCESS_KEY_ID=admin
ARG AWS_SECRET_ACCESS_KEY=supersecret
RUN mkdir /work
WORKDIR /work
COPY . .
RUN pip install jupyter==1.0.0 -U && pip install jupyterlab==3.6.1
RUN pip install -r requirements.txt
EXPOSE 8888
# Copiar script de entrada
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Usar el script como punto de entrada
ENTRYPOINT ["/entrypoint.sh"]