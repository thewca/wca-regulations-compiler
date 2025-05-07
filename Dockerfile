FROM python:3.10.17-bookworm
RUN apt update
RUN apt install -y fonts-unfonts-core fonts-wqy-microhei fonts-ipafont
RUN pip install ply unidecode
COPY . .
RUN mkdir build
RUN python -m wrc.wrc ./wca-regulations.md --target=html --output=build
