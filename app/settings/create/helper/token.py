import tiktoken
from transformers import AutoTokenizer

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

# Mapping of Ollama model names to Hugging Face model IDs
ollama_to_hf_mapping = {
    "qwen3:32b": "Qwen/Qwen2-72B-Instruct",  # Adjust if Ollama specifies a different Qwen model
    "deepseek-r1:32b": "deepseek-ai/DeepSeek-R1",
    "gemma3:27b": "google/gemma-2-27b",  # Assuming Gemma 2; verify if Gemma 3 exists in Ollama
    "mistral:latest": "mistral-ai/Mixtral-8x7B-Instruct-v0.1",  # Adjust based on Ollama's version
    "llama2:13b": "meta-llama/Llama-2-13B",
    "llama3.1:8b": "meta-llama/Llama-3.1-8B",
}

# Initialize Hugging Face tokenizers for Ollama models
hf_tokenizers = {
    model: AutoTokenizer.from_pretrained(hf_model_id, use_fast=True)
    for model, hf_model_id in ollama_to_hf_mapping.items()
}

def count_tokens(text, model="gpt-3.5-turbo"):
    if model in model_encodings:
        tokenizer = model_encodings[model]
    
    elif model in hf_tokenizers:
        tokenizer = hf_tokenizers[model]
    
    tokens = tokenizer.encode(text)
    return len(tokens)    

