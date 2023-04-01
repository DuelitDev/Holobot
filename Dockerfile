FROM ubuntu:jammy

RUN apt-get update && apt-get install -y build-essential nano wget \
    libopus-dev libffi-dev python3-pip && pip install --upgrade pip setuptools wheel
RUN wget https://github.com/DuelitDev/Holobot/archive/refs/tags/v2.4.1.230401.0.tar.gz && \
    tar xf v2.4.1.230401.0.tar.gz && mv Holobot-2.4.1.230401.0 holobot && rm v2.4.1.230401.0.tar.gz
RUN pip install -r /holobot/requirements.txt
ENV HOLOBOT_CONF_PATH /holobot/global-configure.conf

WORKDIR /holobot/
ENTRYPOINT ["python3", "app.py"]
