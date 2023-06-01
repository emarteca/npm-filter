FROM ubuntu:latest
ARG DEBIAN_FRONTEND=noninteractive

# build arg: setting up for a specific repo?
ARG REPO_LINK

RUN apt-get update \
	&& apt-get -y install --no-install-recommends python3 git unzip vim curl gnupg xz-utils parallel

RUN apt update
RUN apt -y install python3-pip
RUN pip3 install bs4 scrapy

RUN mkdir -p /home/npm-filter/results

COPY src /home/npm-filter/
COPY *.sh /home/npm-filter/
COPY get_rel_project_reqs.js /home/npm-filter

WORKDIR /home/npm-filter

RUN git config --global http.sslVerify "false"
RUN ./build.sh $REPO_LINK
