FROM ghcr.io/anthrocon-rams/rams:main
ENV uber_plugins=["anthrocon"]

# install plugins
COPY . plugins/anthrocon/

RUN $HOME/.local/bin/uv pip install --system -r plugins/anthrocon/requirements.txt
