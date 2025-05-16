import tiktoken


# 初始化模型分词器
model_encodings = {
    "gpt-3.5-turbo": tiktoken.encoding_for_model("gpt-3.5-turbo"),
    "gpt-4o-mini": tiktoken.encoding_for_model("gpt-4o-mini"),
    "gpt-4-turbo": tiktoken.encoding_for_model("gpt-4-turbo"),
    "gpt-4o": tiktoken.encoding_for_model("gpt-4o"),
    "text-embedding-ada-002": tiktoken.encoding_for_model("text-embedding-ada-002"),
    "text-embedding-3-large": tiktoken.encoding_for_model("text-embedding-3-large"),
    "text-embedding-3-small": tiktoken.encoding_for_model("text-embedding-3-small")
}


def count_tokens(text, model="gpt-3.5-turbo"):
    """
    根据指定模型计算文本的 token 数量。
    默认使用 GPT-3.5 的分词器。
    """
    if model not in model_encodings:
        raise ValueError(f"Unsupported model '{model}'. Available models: {list(model_encodings.keys())}")
 
    encoding = model_encodings[model]
    tokens = encoding.encode(text)
    return len(tokens)



