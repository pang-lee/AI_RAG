FROM python:3.10.14

# 添加标签
LABEL maintainer="pang@heimavista.com"
LABEL version="1.0"
LABEL description="The heimavista AI chatBot."
LABEL name="AI python app"

# 设置环境变量
ENV VERSION=1.0

# 设置工作目录
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 复制项目的所有文件到工作目录
COPY ./app .

# 设置容器启动时运行的命令
CMD ["python", "index.py"]
