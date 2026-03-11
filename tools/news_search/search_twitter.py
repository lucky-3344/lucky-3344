from agent_reach import AgentReach
import json

agent = AgentReach()

# 搜索Twitter热点
try:
    result = agent.twitter("trending")
    print("Twitter Search Result:")
    print(result)
except Exception as e:
    print(f"Error: {e}")
    print("Trying alternative search...")
    try:
        result = agent.twitter("AI")
        print(result)
    except Exception as e2:
        print(f"Error2: {e2}")
