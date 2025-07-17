FROM python:3.10.17-bookworm
RUN apt update
RUN apt install -y fonts-unfonts-core fonts-wqy-microhei fonts-ipafont wget tar
RUN wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.4/wkhtmltox-0.12.4_linux-generic-amd64.tar.xz -O wkhtml.tar.xz && tar -xf wkhtml.tar.xz --strip-components=1 -C /usr/local
RUN pip install ply unidecode
COPY . .
RUN mkdir build
RUN python -m wrc.wrc ./wca-regulations.md --target=check --output=build
RUN python -m wrc.wrc ./wca-regulations.md --target=pdf --output=build
RUN python -m wrc.wrc ./wca-regulations.md --target=html --output=build
