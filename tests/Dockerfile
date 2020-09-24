FROM ubuntu:18.04

RUN apt-get update \
	&& DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends python3 python3-pip git 
RUN pip3 install --upgrade setuptools
RUN pip3 install scrapy bs4

RUN mkdir -p /home/playground

COPY ../*.py /home/playground/
COPY *.sh /home/playground/
COPY default_filter_config.json /home/playground/

WORKDIR /home/playground

RUN ./build.sh
