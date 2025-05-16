#!/bin/sh

# 啟動 Ollama 服務器（後台運行）
/bin/ollama serve &

# 儲存 Ollama 服務器的 PID
OLLAMA_PID=$!

# 等待 Ollama 服務器準備就緒
echo "Waiting for Ollama server to be ready..."
sleep 10
echo "Ollama server is assumed ready!"

# 從環境變量 OLLAMA_MODELS 獲取模型清單並下載
if [ -n "$OLLAMA_MODELS" ]; then
  echo "Pulling models: $OLLAMA_MODELS"
  # 使用 echo 和管道將逗號分隔的模型清單轉換為陣列
  echo "$OLLAMA_MODELS" | tr ',' '\n' | while read -r model; do
    echo "Pulling model: $model"
    /bin/ollama pull "$model"
  done
else
  echo "No models specified in OLLAMA_MODELS environment variable."
fi

# 等待後台的 Ollama 服務器進程
wait $OLLAMA_PID