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


class TTSTalker:
    def __init__(self):
        pass

    def generate(self, text, choice):
        return "output.mp3"


# 聊天窗口显示用户输入
def user(query, history, doc_list):  # 输入输出为msg_btn的inputs和outputs
    # 获取c_range_id
    if doc_list != "":
        c_range_id = c_range_id_dic[doc_list]
        history += [[query, None]]
    return "", history


# 聊天窗口显示机器返回
def bot(history):  # 输入输出均传给chatbot控件
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
    doc_list = list(c_range_id_dic.keys())
    for key in c_range_id_dic.keys():
        # 尝试找到value
        if c_range_id_dic[key] == c_range_id:
            doc_name = key
            return gr.Dropdown.update(choices=doc_list, value=doc_name)
    # 不存在合适的value则用户选择
    return gr.Dropdown.update(choices=doc_list)


with gr.Blocks() as demo:
    gr.Markdown("<div align='center'> <h1> Zhoulab金融文本大模型问答</span> </h1> </div>")
    # 最上方文字输入栏，放置问题
    with gr.Row(variant='panel'):
        with gr.Column(varient='panel'):
            msg_box = gr.Textbox(
                show_label=False,
                placeholder="请输入问题："
            ).style(container=False)
        with gr.Column(scale=1):
            msg_button = gr.Button("发送问题")

    with gr.Row().style(equal_height=True):
        # 左：问答模块，包括对话框、文件上传框
        with gr.Column(variant='panel'):
            chatbot = gr.Chatbot([], elem_id="chatbot", label="招股书问答")
            with gr.Row():
                with gr.Column(scale=3, min_width=400):
                    file_dropdown = gr.Dropdown(
                        choices=list(c_range_id_dic.keys()),
                        show_label=False,
                        interactive=True
                    ).style(container=False)
                with gr.Column(scale=1, min_width=112):
                    upload_button = gr.UploadButton("📁", file_types=["file"])

        # 右：机器人输出渲染模块，包括图片上传、音频风格生成、渲染设置
        with gr.Column(variant='panel'):
            with gr.Row(variant='panel'):
                source_image = gr.Image(label="Source image", source="upload", type="filepath",
                                        elem_id="img2img_image").style(width=512)

            with gr.Row(variant='panel'):
                # TODO 此处直接用GLM的回复生成语音
                # from text_to_speech import TTSTalker
                tts_talker = TTSTalker()
                with gr.Column(variant='panel'):
                    # voice_choice = gr.inputs.Dropdown(label="Input text",
                    #                                   choices=list(tts_talker.voice_dict.keys()))
                    voice_choice = gr.inputs.Dropdown(label="Voice choice",
                                                      choices=['option1', 'option2'])
                    input_text = gr.Textbox(label="Input text", lines=3,
                                                placeholder="Enter the text that drives the 2D Digital Human")
                    tts = gr.Button('Generate audio', elem_id="sadtalker_audio_generate", variant='primary')
                    driven_audio = gr.Audio(label="Driven audio", format="wav", type="filepath")
                    tts.click(fn=tts_talker.generate, inputs=[input_text, voice_choice], outputs=[driven_audio])

            with gr.Tabs(elem_id="generate_setting"):
                with gr.TabItem('Generation Settings'):
                    with gr.Row():
                        batch_size = gr.Slider(label="batch size in generation", step=1, minimum=1, maximum=24, value=24)
                        enhancer = gr.Checkbox(label="GFPGAN as Face enhancer (a little slow)")
                        submit = gr.Button('Generate', elem_id="sadtalker_generate", variant='primary')

    # 生成视频输出栏
    with gr.Row(variant='panel'):
        gen_video = gr.Video(label="Generated video", format="mp4")

    msg_button.click(fn=user, inputs=[msg_box, chatbot, file_dropdown], outputs=[msg_box, chatbot], queue=False).then(
        bot, chatbot, chatbot
    )
    upload_button.upload(add_file, [upload_button, file_dropdown], file_dropdown)
    demo.load(load, file_dropdown, file_dropdown)

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=9030)
