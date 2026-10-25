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

# Checks (compile, lint, the agent's own testbench, which may be model-written Python) run as this unprivileged
# user, without the key in their environment, so they cannot read the agent's environment through /proc.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin cvdptool
ENV CVDP_TOOL_USER=cvdptool

# Claude Code, pinned, for the claudecode comparison harness only (CVDP_HARNESS=claudecode); the other harnesses
# never call it.
ARG CLAUDE_CODE_VERSION=2.1.310
ENV DISABLE_AUTOUPDATER=1 DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1
RUN (command -v curl || (apt-get update -qq && apt-get install -y -qq --no-install-recommends curl ca-certificates)) && \
    curl -fsSL https://claude.ai/install.sh | bash -s ${CLAUDE_CODE_VERSION} && \
    install -m 0755 "$(readlink -f /root/.local/bin/claude)" /usr/local/bin/claude && rm -rf /root/.local/bin/claude && \
    claude --version  # a real copy: the harness runs the agent as a non-root user, who cannot reach /root

COPY agent/cvdp_agent /opt/agent/cvdp_agent
# M3c: the mutation gate needs Yosys' `mutate -ctrl` (core Yosys since 0.9); the interface check needs pyslang
RUN command -v iverilog && command -v verilator && command -v yosys && python3 -c "import cocotb_tools" && \
    yosys -h mutate | grep -q -- "-ctrl" && /opt/agent/venv/bin/python -c "import pyslang" && \
    cd /opt/agent && /opt/agent/venv/bin/python -m cvdp_agent --mermaid > /dev/null

WORKDIR /code
ENV PYTHONPATH=/opt/agent
ENTRYPOINT ["/opt/agent/venv/bin/python", "-m", "cvdp_agent"]
