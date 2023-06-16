FROM ubuntu:latest
ARG DEBIAN_FRONTEND=noninteractive

# build arg: setting up for a specific repo? at a specific commit?
ARG REPO_LINK
ARG REPO_COMMIT

RUN apt-get update \
	&& apt-get -y install --no-install-recommends python3 git unzip vim curl gnupg xz-utils parallel

RUN apt update
RUN apt -y install python3-pip
RUN pip3 install bs4 scrapy xmltodict pandas

RUN mkdir -p /home/npm-filter/results
RUN mkdir /home/npm-filter/src
RUN mkdir /home/npm-filter/configs

COPY src /home/npm-filter/src
COPY configs /home/npm-filter/configs
COPY *.sh /home/npm-filter/
COPY get_rel_project_reqs.js /home/npm-filter

WORKDIR /home/npm-filter

RUN git config --global http.sslVerify "false"
RUN ./build.sh $REPO_LINK $REPO_COMMIT
# source the env variables produced by the build script (node version, etc)
RUN . /envfile

# add a default command for running the tests for repo_link and commit provided
# this runs in verbose mode
# need to use ENV instead of ARG in the CMD b/c docker is 10/10
ENV ENV_REPO_COMMIT=$REPO_COMMIT
ENV ENV_REPO_LINK=$REPO_LINK
# gotta source our env vars so the command can run and use npm/node/etc :-)
CMD . /envfile; ./run_verbose_for_repo_and_config.sh $ENV_REPO_LINK $ENV_REPO_COMMIT