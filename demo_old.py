# -*- coding: utf-8 -*-
# Date       ：2023/6/12
# Author     ：Chen Xuekai
# Description：

"""
流程：
上传文件
1、读取文件为字符串列表
2、生成摘要
3、拼接成上下文问答对 {原文段：原文段上下1行}
4、送入FAISS建立索引（是否使用BertModel进行embedding？）

提问
1、查找与问题最相似的上下文，返回背景段落
2、将相似段落与历史段落拼接成text(Q,A)形式送入ChatGLM-6B，返回答案
"""
import yaml
import gradio as gr
import asyncio
from sentence_transformers import SentenceTransformer as SBert
from query2glm import ChatGLM
from processFile.fileProcess import ProcessBook

with open("config.yaml") as f:
    config = yaml.safe_load(f)

encode_model = SBert(config['encode_model_path'])
glm_chater = ChatGLM(chat_url=config['chatglm6b_url'], faiss_path=config['faiss_path'], encode_model=encode_model)
global c_range_id
history_id_dic = {}  # {id: history_list}
c_range_id_dic = {}  # {文件名：md5_id}


with gr.Blocks() as demo:
    chatbot = gr.Chatbot([], elem_id="chatbot", label="招股书问答").style(height=600)
    with gr.Row():
        with gr.Column(scale=0.85):
            msg_box = gr.Textbox(
                show_label=False,
                placeholder="请输入问题："
            ).style(container=False)
        with gr.Column(scale=0.15):
            msg_button = gr.Button("发送问题")
    with gr.Row():
        with gr.Column(scale=0.85):
            file_dropdown = gr.Dropdown(
                choices=list(c_range_id_dic.keys()),
                show_label=False,
                interactive=True
            ).style(container=False)
        with gr.Column(scale=0.15):
            upload_button = gr.UploadButton("📁", file_types=["file"])


    # 聊天窗口显示用户输入
    def user(query, history, doc_list):  # 输入输出为msg_btn的inputs和outputs
        global c_range_id
        global c_range_id_dic
        # 获取c_range_id
        if doc_list != "":
            c_range_id = c_range_id_dic[doc_list]
            history += [[query, None]]
        return "", history


    # 聊天窗口显示机器返回
    def bot(history):  # 输入输出均传给chatbot控件
        global c_range_id
        global file_dropdown
        global history_id_dic
        print(c_range_id)
        query = history[-1][0]
        if query[-1] not in [",", ".", "?", "!", "，", "。", "？", "！"]:
            query1 = query + "？"
        else:
            query1 = query
        if c_range_id == "":
            response = "请导入文件"
        else:
            response = asyncio.run(glm_chater.generate(c_range_id, query1, history=history_id_dic[c_range_id]))
        history[-1][1] = response
        history_id_dic[c_range_id].append([query1, response])
        return history


    # 上传文件
    def add_file(file, doc_list):
        global c_range_id
        global c_range_id_dic
        global history_id_dic
        preprocess = ProcessBook(encode_model, **config['header_and_footer'])
        c_range_id = preprocess.upload(config['faiss_path'], file.name)
        doc_name = file.name.split("/")[-1]
        c_range_id_dic[doc_name] = c_range_id
        doc_list = list(c_range_id_dic.keys())
        if c_range_id not in history_id_dic:  # 初次上传，初始化文件history
            history_id_dic[c_range_id] = []
        return gr.Dropdown.update(choices=doc_list, value=doc_name)


    # 页面启动执行的内容
    def load(doc_list):
        global c_range_id
        global c_range_id_dic
        global history_id_dic

        doc_list = list(c_range_id_dic.keys())
        for key in c_range_id_dic.keys():
            # 尝试找到value
            if c_range_id_dic[key] == c_range_id:
                doc_name = key
                return gr.Dropdown.update(choices=doc_list, value=doc_name)
        # 不存在合适的value则用户选择
        return gr.Dropdown.update(choices=doc_list)


    msg_button.click(fn=user, inputs=[msg_box, chatbot, file_dropdown], outputs=[msg_box, chatbot], queue=False).then(
        bot, chatbot, chatbot
    )
    upload_button.upload(add_file, [upload_button, file_dropdown], file_dropdown)
    demo.load(load, file_dropdown, file_dropdown)

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=9031)
