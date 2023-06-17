# -*- coding: utf-8 -*-
# Date       ：2023/6/12
# Author     ：Chen Xuekai
# Description：将背景背景塞入prompt，并与ChatGLM-6b对话
import requests
import json
import jieba.analyse
import re
import os
import faiss  # 注意，这个不能在引用BERT之前引入


class ChatGLM:
    def __init__(self, chat_url, faiss_path, encode_model):
        self.faiss_path = faiss_path
        self.chatglm6b_url = chat_url
        self.encode_model = encode_model

    def post_to_6b(self, article, question, history):
        history_prompt = ""
        history = history[-5:]  # 限制近5轮对话
        for i in range(len(history)):
            history_prompt = history_prompt + "Q：" + history[i][0] + "\n"
            history_prompt = history_prompt + "A：" + history[i][1] + "\n"

        prompt = f"""
        Q：你是一个AI助手，严格遵照我所提供的知识回答问题。\
        A：知道了，我会严格按照您所提供的知识回答问题。\
        {article}
        {history_prompt}
        Q：{question}，回答之前让我们先想一想你的答案是否有依据。\
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
        # 根据关键词判断
        # result["response"] = self.result_clean(article + history_prompt, result["response"])
        # TODO 处理返回结果
        return result["response"]

    def result_clean(self, article, result):
        # TODO 这个在干啥？可能不是很必要
        # 语句分拆
        result_sen = re.split(r"([。?？!！])", result)
        result_sen.append("")
        result_sen = ["".join(i) for i in zip(result_sen[0::2], result_sen[1::2])]

        # 逐句检验
        clean_sen = []
        for sen in result_sen:
            # 过短的句子不检验
            if len(sen) < 10:
                clean_sen.append(sen)
                continue
            # 通过模型创造的关键词占比验证
            sen_kw = jieba.analyse.extract_tags(sen,
                                                topK=max(int(0.05 * len(sen)), 3),
                                                withWeight=False)

            sen_kw = list(set(sen_kw))
            create_num = 0
            for kw in sen_kw:
                if kw not in article:
                    create_num += 1
            if create_num > 0.5 * len(sen_kw):
                print(create_num, len(sen_kw), sen_kw, sen)
                continue
            else:
                clean_sen.append(sen)

        # 生成结果
        if len(clean_sen) < 0.3 * len(result_sen):
            clean_res = "您问的问题在所给文本中没有答案，以下是我可以提供的答案：\n" + article
        else:
            clean_res = "".join(clean_sen)

        return clean_res

    async def generate(self, faq_id: str, query: str, history):
        # 找最相似的上下文article
        index_db = faiss.read_index(os.path.join(self.faiss_path, faq_id, "index_db.index"))
        with open(os.path.join(self.faiss_path, faq_id, "context_pair.json"), 'r') as jsonfile:
            qa_pair_list = json.load(jsonfile)
        query_embedding = self.encode_model.encode([query])
        _, top_id = index_db.search(query_embedding, 2)  # TODO 加上confidence判断，剔除无关的上下文
        most_sim_id = int(top_id[0][0])
        context = qa_pair_list[most_sim_id][1]

        # post_to_6b
        answer = self.post_to_6b(context, query, history)

        return answer
