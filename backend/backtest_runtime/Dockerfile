FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /runtime

RUN pip install --no-cache-dir rqalpha==6.3.0

COPY run_rqalpha.py /runtime/run_rqalpha.py
COPY rqalpha_mod_quant_lab /runtime/rqalpha_mod_quant_lab

RUN useradd --uid 65532 --create-home runner
USER 65532:65532

ENTRYPOINT ["python", "/runtime/run_rqalpha.py"]
