# The agent image: the CVDP simulation image (Icarus, Verilator, Yosys, cocotb) plus the agent in its own venv,
# so the agent's Python packages never touch the harness's /venv that cocotb runs from.
ARG SIM_IMAGE=ghcr.io/brendanjameslynskey/cvdp-sim:8e894cf
FROM ${SIM_IMAGE}

ARG AGENT_VERSION=dev
ENV CVDP_AGENT_VERSION=${AGENT_VERSION} \
    LANGCHAIN_TRACING_V2=false \
    LANGSMITH_TRACING=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY agent/requirements.txt /opt/agent/requirements.txt
RUN uv venv /opt/agent/venv && \
    uv pip install --python /opt/agent/venv/bin/python -r /opt/agent/requirements.txt

COPY agent/cvdp_agent /opt/agent/cvdp_agent
RUN command -v iverilog && command -v verilator && command -v yosys && python3 -c "import cocotb_tools" && \
    cd /opt/agent && /opt/agent/venv/bin/python -m cvdp_agent --mermaid > /dev/null

WORKDIR /code
ENV PYTHONPATH=/opt/agent
ENTRYPOINT ["/opt/agent/venv/bin/python", "-m", "cvdp_agent"]
