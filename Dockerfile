FROM ubuntu:jammy

RUN apt-get update && apt-get install -y nano wget python3.11 python3-pip libopus-dev && \
    wget https://github.com/DuelitDev/Holobot/archive/refs/tags/v2.4.1.230331.1.tar.gz && \
    tar xf v2.4.1.230331.1.tar.gz && mv Holobot-2.4.1.230331.1 holobot && \
    rm v2.4.1.230331.1.tar.gz && pip install -r /holobot/requirements.txt
RUN echo "python3 /holobot/app.py" > /etc/init.d/holobot.sh
ENV HOLOBOT_CONF_PATH /holobot/global-configure.conf

WORKDIR /holobot/
CMD ["python3", "/holobot/app.py"]

