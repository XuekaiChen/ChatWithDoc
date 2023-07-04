# -*- coding: utf-8 -*-
# Date       ：2023/6/13
# Author     ：Chen Xuekai
# Description：
import os.path
import json
import time
import hashlib
import pickle
from textrank4zh import TextRank4Sentence
from processFile.txtReader import ProcessTxt
from processFile.docxReader import ProcessDocx
from processFile.pdfReader import ProcessPdf
import faiss


def string_to_md5(s):
    md5_val = hashlib.md5(s.encode('utf8')).hexdigest()
    return md5_val


class ProcessBook:
    def __init__(self, encode_model, header=False, footer=False) -> None:
        self.tr4s = TextRank4Sentence()
        self.process_pdf = ProcessPdf(header=header, footer=footer)
        self.process_docx = ProcessDocx()
        self.process_txt = ProcessTxt()
        self.encode_model = encode_model

    def get_key_sentence(self, text, num=10):  # 过短文本没有摘要
        self.tr4s.analyze(text=text, lower=True, source='all_filters')
        all_sent = []
        for item in self.tr4s.get_key_sentences(num=num):
            all_sent.append((item.index, item.sentence))

        all_sent = sorted(all_sent, key=lambda x: x[0])
        out = ""
        for line in all_sent:
            out += line[1]
        return out

    def build_QApair(self, paras_list):
        # 整合为键值对
        faq_list = []
        for i in range(len(paras_list)):
            temp = (paras_list[i], "\n".join(paras_list[i - 1:i + 2]))
            faq_list.append(temp)

        # 末段置为全书摘要
        text = "\n".join(paras_list)
        s = time.time()
        abstract = self.get_key_sentence(text[:10000], 6)
        print(f"{len(text)}字摘要时间{time.time() - s}")
        print("摘要内容：")
        print(abstract)
        abst = ("文档主要说了什么？", "全书的主要内容是：" + "\n" + abstract)
        faq_list.append(abst)
        print(f"faq 入库：{len(faq_list)} 条")

        return faq_list

    def upload(self, faiss_path: str, file_path: str):
        # 识别文件类型，处理成paras列表
        paras = []
        para_page = []
        file_suffix = file_path.split("/")[-1].split(".")[-1]
        if file_suffix == "docx" or file_suffix == "doc":
            paras = self.process_docx.get_paras(file_path)
        elif file_suffix == "pdf":
            paras, para_page = self.process_pdf.get_paras(file_path)
        elif file_suffix == "txt":
            paras = self.process_txt.get_paras(file_path)

        # 建立索引
        qa_pair_list = self.build_QApair(paras)
        query_list = [pair[0] for pair in qa_pair_list]
        query_embedding = self.encode_model.encode(query_list)
        index_db = faiss.IndexFlatL2(query_embedding.shape[1])
        index_db.add(query_embedding)

        # 存储索引库
        md5_str = string_to_md5(file_path)
        if not os.path.exists(faiss_path):
            os.makedirs(faiss_path)
        if not os.path.exists(os.path.join(faiss_path, md5_str)):
            os.makedirs(os.path.join(faiss_path, md5_str))
        faiss.write_index(index_db, os.path.join(faiss_path, md5_str, "index_db.index"))
        # 存储context问答对
        with open(os.path.join(faiss_path, md5_str, "context_pair.json"), "w") as jsonfile:
            json.dump(qa_pair_list, jsonfile)
        with open(os.path.join(faiss_path, md5_str, "paragraph_pages.data"), "wb") as f:
            para_page.append([])  # 摘要FAQ没有对应页码
            pickle.dump(para_page, f)

        return md5_str
