import requests
import json

test_url = "http://10.112.9.164:8001/api/chat"

test_json = {'according':'根据申报材料：原始报表与申报报表存在多项会计核算差错调整事项。'}
test_post = requests.post(url=test_url, json=test_json)

response = json.loads(test_post.text)
print(response)