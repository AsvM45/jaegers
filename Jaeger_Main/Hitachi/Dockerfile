# Wacky Wheels Control Tower: dashboard + tower + the AI model, in one container.
# Built for Hugging Face Spaces (free CPU tier: 2 vCPU, 16 GB RAM). Listens on $PORT (7860 there).
#
#   docker build -t control-tower .
#   docker run -p 7860:7860 -e TOWER_PASSWORD=choose-one control-tower

# 1) Build the React dashboard.
FROM node:20-bookworm-slim AS web
WORKDIR /web
COPY tower/ui/web/package.json tower/ui/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tower/ui/web/ ./
RUN npm run build

# 2) The tower (Python standard library only), Ollama and the qwen3:1.7b model.
FROM python:3.11-slim-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates zstd \
 && rm -rf /var/lib/apt/lists/*

# Ollama for CPU. The GPU libraries are removed: Spaces' free tier has no GPU, and they are most of the size.
ENV OLLAMA_MODELS=/opt/ollama/models
RUN curl -fsSL https://ollama.com/install.sh | sh \
 && rm -rf /usr/local/lib/ollama/cuda_* /usr/local/lib/ollama/rocm* /usr/lib/ollama/cuda_* /usr/lib/ollama/rocm* 2>/dev/null || true
# The model is baked into the image, so a restart does not download it again.
RUN mkdir -p "$OLLAMA_MODELS" \
 && (ollama serve >/tmp/ollama.log 2>&1 &) \
 && for i in $(seq 1 30); do curl -sf http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done \
 && ollama pull qwen3:1.7b \
 && chmod -R a+rX /opt/ollama

# Spaces run the container as user 1000; it owns the app so the tower can write its run files.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PYTHONUNBUFFERED=1 \
    TOWER_HOST=0.0.0.0 \
    TOWER_PUBLIC=1 \
    PORT=7860 \
    RUN_OLLAMA=1 \
    OLLAMA_NUM_PARALLEL=2 \
    TOWER_LLM_MODEL=qwen3:1.7b \
    TOWER_TOOL_MODEL=qwen3:1.7b
WORKDIR /home/user/app
COPY --chown=user . .
COPY --chown=user --from=web /dist ./tower/ui/dist
RUN chmod +x deploy/start.sh
EXPOSE 7860
CMD ["deploy/start.sh"]
