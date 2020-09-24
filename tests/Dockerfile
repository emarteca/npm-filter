FROM ubuntu:18.04

RUN apt-get update \
	&& DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends python3 python3-pip git vim
RUN pip3 install --upgrade setuptools
RUN pip3 install scrapy bs4

RUN mkdir -p /home/playground

COPY . /home/playground/

WORKDIR /home/playground

RUN ./build.sh
