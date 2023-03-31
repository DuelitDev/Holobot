FROM ubuntu:jammy

RUN apt-get update && apt-get install -y nano wget python3.11 python3-pip libopus-dev
RUN wget https://github.com/DuelitDev/Holobot/archive/refs/tags/v2.4.1.230331.7.tar.gz && \
    tar xf v2.4.1.230331.7.tar.gz && mv Holobot-2.4.1.230331.7 holobot && \
    rm v2.4.1.230331.7.tar.gz
RUN pip install -r /holobot/requirements.txt
ENV HOLOBOT_CONF_PATH /holobot/global-configure.conf

WORKDIR /holobot/
ENTRYPOINT ["python3", "app.py"]

