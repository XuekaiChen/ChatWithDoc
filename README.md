# ChatWithDoc
大语言模型ChatGLM-6B为基座，接入文档阅读功能进行实时问答，可上传txt/docx/pdf多种文件类型。
### 内容比对
![问答示例](img/example.png)
### 显示参考依据
![问答参考](img/with_ref.png)
## 目前功能
- 支持较少页数的文档理解
- 支持问题的定位
- 支持多轮交互问答
- 支持txt / docx / pdf多种文件类型的输入
- 可在聊天过程中自由切换文档，切换后延续本篇文档的对话历史
- PDF文档问答中加入参考依据

### API部署
运行
```
python api.py
```

请求
```
file_path = "reference_file.pdf"
data = {"prompt": "这篇文章主要讲了什么？", "history": []}
multipart_data = {
    'json': (None, json.dumps(data), 'application/json'),
    'file': (open(file_path, 'rb'))
}
response = requests.post(url, files=multipart_data)
```

得到返回值
```

```