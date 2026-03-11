import requests

url = "http://127.0.0.1:8000/convert"
files = {"file": open("path/to/input.pdf", "rb")}
params = {"dpi": 150}

response = requests.post(url, files=files, params=params)

if response.status_code == 200:
    with open("output.ofd", "wb") as f:
        f.write(response.content)
    print("转换成功，已保存为 output.ofd")
else:
    print(f"转换失败: {response.status_code}")
    print(response.text)
