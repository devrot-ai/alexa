# FreshKeep — single-container deploy (Render / Hugging Face Spaces / fly.io)
# Runs BOTH the MCP server (:8811) and the simulator, which speaks MCP to it.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY freshkeep ./freshkeep
COPY skill ./skill
COPY LICENSE README.md ./

# Platforms (Render/HF) inject PORT for the web service.
ENV FRESHKEEP_MCP_HOST=0.0.0.0 \
    FRESHKEEP_SIM_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

EXPOSE 8800 8811
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8800')+'/healthz',timeout=3)"

CMD ["sh", "-c", "python -m freshkeep.mcpserver & python -m freshkeep.simulator.app"]
