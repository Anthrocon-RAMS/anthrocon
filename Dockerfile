FROM ghcr.io/magfest/ubersystem:main
ENV uber_plugins=["anthrocon"]

# install plugins
COPY . plugins/anthrocon/

RUN uv pip install --system -r plugins/anthrocon/requirements.txt