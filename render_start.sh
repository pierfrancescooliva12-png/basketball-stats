#!/usr/bin/env bash
# Avvio su Render: i Secrets arrivano come file segreto (/etc/secrets/secrets.toml) e Streamlit li
# legge da .streamlit/secrets.toml; la porta la decide Render ($PORT).
set -euo pipefail
if [ -f /etc/secrets/secrets.toml ]; then
  mkdir -p .streamlit
  cp /etc/secrets/secrets.toml .streamlit/secrets.toml
fi
exec streamlit run streamlit_app.py \
  --server.port "${PORT:-8501}" --server.address 0.0.0.0 --server.headless true
