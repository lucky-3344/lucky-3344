"""
AI模型自动切换脚本
优先使用 MiniMax，如果失败则自动切换到 Kimi (NVIDIA)
"""

import requests
import json

# ============== 配置 ==============
# MiniMax 配置
MINIMAX_API_KEY = "your-minimax-key"
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"

# NVIDIA Kimi 配置
NVIDIA_API_KEY = "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"

def call_minimax(prompt, model="MiniMax-Text-01"):
    """调用 MiniMax API（MiniMax-Text-01 为当前主力模型，免费套餐可用；M2.5 需高级套餐）"""
    url = f"{MINIMAX_BASE_URL}/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            print(f"MiniMax 错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"MiniMax 异常: {e}")
        return None

def call_kimi(prompt):
    """调用 NVIDIA Kimi API"""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "moonshotai/kimi-k2.5",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            print(f"Kimi 错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"Kimi 异常: {e}")
        return None

def chat(prompt):
    """
    主对话函数 - 自动切换
    1. 先尝试 MiniMax
    2. 失败则切换到 Kimi
    """
    print("🤖 尝试 MiniMax...")
    result = call_minimax(prompt)
    
    if result:
        print("✅ 使用 MiniMax 成功")
        return f"[MiniMax]\n{result}"
    else:
        print("⚠️ MiniMax 失败，切换到 Kimi...")
        result = call_kimi(prompt)
        if result:
            print("✅ 使用 Kimi 成功")
            return f"[Kimi]\n{result}"
        else:
            return "❌ 两个模型都失败了"

if __name__ == "__main__":
    prompt = input("请输入问题: ")
    response = chat(prompt)
    print("\n" + "="*50)
    print(response)
