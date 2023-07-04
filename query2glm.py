# -*- coding: utf-8 -*-
# Date       ：2023/6/12
# Author     ：Chen Xuekai
# Description：将背景背景塞入prompt，并与ChatGLM-6b对话
import requests
import json
import jieba.analyse
import re
import pickle
import os
import faiss  # 注意，这个不能在引用BERT之前引入


class ChatGLM:
    def __init__(self, chat_url, faiss_path, encode_model):
        self.faiss_path = faiss_path
        self.chatglm6b_url = chat_url
        self.encode_model = encode_model

    def post_to_6b(self, article, page, question, history):
        if page:
            article = f'依据来自文本第{page}页段落：{article}'

        history_prompt = ""
        history = history[-5:]  # 限制近5轮对话
        for i in range(len(history)):
            history_prompt = history_prompt + "Q：" + history[i][0] + "\n"
            history_prompt = history_prompt + "A：" + history[i][1] + "\n"

        # prompt形式：Information-injected Dialogue-formatted prompt
        prompt = f"""
        Q：你是一个AI助手，严格遵照我所提供的知识回答问题。\
        A：知道了，我会严格按照您所提供的知识回答问题。\
        {article}
        {history_prompt}
        Q：{question}，回答的最后给出参考依据。\
        A：
        """

        data = {"prompt": prompt, "history": history}
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers = {'Content-Type': 'application/json'}
        res = requests.request("post", self.chatglm6b_url, headers=headers, data=payload)
        if not res.status_code == 200:
            return "ChatGLM访问失败，无法提供答案。"
        result = json.loads(res.text)
        print(result)
        return result["response"]

    async def generate(self, faq_id: str, query: str, history):
        # 找最相似的上下文article
        index_db = faiss.read_index(os.path.join(self.faiss_path, faq_id, "index_db.index"))
        with open(os.path.join(self.faiss_path, faq_id, "context_pair.json"), 'r') as jsonfile:
            qa_pair_list = json.load(jsonfile)
        with open(os.path.join(self.faiss_path, faq_id, "paragraph_pages.data"), "rb") as f:
            para_pages = pickle.load(f)

        query_embedding = self.encode_model.encode([query])
        # TODO 添加跨范围回答功能，并标注依据（建立索引时加入页码）
        #  方法：查找top3相关上下文，用confidence剔除无关的上下文
        _, top_id = index_db.search(query_embedding, 2)  # top_id:(1, top_k)  _:[[8.93..,9.68..]]数越大越不相关
        most_sim_id = int(top_id[0][0])
        context = qa_pair_list[most_sim_id][1]

        # 加入参考页码
        page_ref = None
        if para_pages != [] and para_pages != [[]]:
            page_ref = para_pages[most_sim_id]

        # post_to_6b
        answer = self.post_to_6b(context, page_ref, query, history)

        return answer
