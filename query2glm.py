# -*- coding: utf-8 -*-
# Date       ：2023/6/12
# Author     ：Chen Xuekai
# Description：将背景背景塞入prompt，并与ChatGLM-6b对话
import os
import requests
import json
import jieba
import pickle
from classifier.classifier import Classifier
from sentence_transformers import SentenceTransformer as SBert
import faiss  # 注意，这个不能在引用BERT之前引入

class ChatGLM:
    def __init__(self, config):
        self.faiss_path = config['faiss_path']
        self.chatglm6b_url = config['chatglm6b_url']
        self.reportglm_url = config['reportglm_url']
        self.encode_model = SBert(config['encode_model_path'])
        self.classify_model = Classifier(config["intention_classifier_model"])
        self.similar_topk = 2

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

    def post_to_genReport(self, article, question):
        prompt = f"根据申报材料：{article}。请依据以上内容，针对“{question}”问题生成质询报告。"
        data = {"according": prompt, "history": []}
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers = {'Content-Type': 'application/json'}
        res = requests.request("post", self.reportglm_url, headers=headers, data=payload)

        if not res.status_code == 200:
            return "生成报告API功能出现错误！"
        result = json.loads(res.text)
        print(result["question"])

        return result["question"]

    async def generate(self, faq_id: str, query: str, history):
        # 1、检索最相似的上下文article
        index_db = faiss.read_index(os.path.join(self.faiss_path, faq_id, "index_db.index"))
        with open(os.path.join(self.faiss_path, faq_id, "context_pair.json"), 'r') as jsonfile:
            qa_pair_list = json.load(jsonfile)
        with open(os.path.join(self.faiss_path, faq_id, "paragraph_pages.data"), "rb") as f:
            para_pages = pickle.load(f)

        query_embedding = self.encode_model.encode([query])
        # TODO 添加跨范围回答功能，并标注依据（建立索引时加入页码）
        #  方法：查找top3相关上下文，用confidence剔除无关的上下文
        _, top_id = index_db.search(query_embedding, self.similar_topk)  # _:[[8.93..,9.68..]]  top_id:(1, top_k)  数越大越不相关

        # 2、意图分类：生成报告 or 问答
        words = " ".join(jieba.cut(query))
        category, confidence = self.classify_model.predict(words)

        # 对于生成报告，post_to_lora，直接返回报告
        if category == "report":
            # 整理问询依据
            information = ""
            for idx, i in enumerate(top_id[0]):
                information += f"（{idx+1}）{qa_pair_list[i][1]}"
            answer = self.post_to_genReport(information, query)

        # 问答，拼接历史和相关段落，问询ChatGLM-6b
        else:
            most_sim_id = int(top_id[0][0])
            context = qa_pair_list[most_sim_id][1]

            # 加入参考页码
            page_ref = None
            if para_pages != [] and para_pages != [[]]:
                page_ref = para_pages[most_sim_id]

            # 对于问答，post_to_6b，附上依据
            answer = self.post_to_6b(context, page_ref, query, history)

        return answer
