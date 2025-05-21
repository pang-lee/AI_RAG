# 使用cuda的image檔並安裝套件啟動整體服務
FROM nvidia/cuda:12.8.0-devel-ubuntu24.04

# 添加標籤
LABEL maintainer="pang@heimavista.com"
LABEL version="1.0"
LABEL description="The heimavista AI chatBot."
LABEL name="AI python app"

# 設置環境變量
ENV VERSION=1.0

# 安裝基本工具和依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    curl \
    libncursesw5-dev \
    xz-utils \
    libffi-dev \
    liblzma-dev \
    && rm -rf /var/lib/apt/lists/*

# 下載並編譯 Python 3.10.14
RUN wget https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tar.xz \
    && tar -xf Python-3.10.14.tar.xz \
    && cd Python-3.10.14 \
    && ./configure --enable-optimizations \
    && make -j$(nproc) \
    && make altinstall \
    && cd .. \
    && rm -rf Python-3.10.14 Python-3.10.14.tar.xz

# 設置 Python 3.10 為默認 python 和 pip
RUN ln -s /usr/local/bin/python3.10 /usr/local/bin/python \
    && ln -s /usr/local/bin/pip3.10 /usr/local/bin/pip

# 設置 CUDA 環境變量
ENV PATH=/usr/local/cuda-12.8/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:${LD_LIBRARY_PATH}

# 設置工作目錄
WORKDIR /app

# 複製並安裝 Python 依賴
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 複製項目文件
COPY ./app .

# 設置容器啟動命令
CMD ["python", "index.py"]


## 使用Python的image檔啟動整體服務
# FROM python:3.10.14

# # 添加标签
# LABEL maintainer="pang@heimavista.com"
# LABEL version="1.0"
# LABEL description="The heimavista AI chatBot."
# LABEL name="AI python app"

# # 设置环境变量
# ENV VERSION=1.0

# # 设置工作目录
# WORKDIR /app

# COPY requirements.txt ./
# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt && \
#     pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# # 复制项目的所有文件到工作目录
# COPY ./app .

# # 设置容器启动时运行的命令
# CMD ["python", "index.py"]
