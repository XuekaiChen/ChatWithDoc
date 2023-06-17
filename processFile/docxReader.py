# -*- coding: utf-8 -*-
# Date       ：2023/6/13
# Author     ：Chen Xuekai
# Description：
from docx import Document
import re


class ProcessDocx:
    def __init__(self):
        pass

    def chinese_detection(self, string_word):
        """
        传入字符串，判断是否包含中文
        :param string_word: 传入的要检测的是否含有中文的字符串
        :return: True or False
        """
        zh_pattern = re.compile('[\u4e00-\u9fa5]+')
        if re.search(pattern=zh_pattern, string=string_word):
            return True
        else:
            return False

    def get_paras(self, path):
        document = Document(path)
        paras = []
        count = 0
        for idx, paragraph in enumerate(document.paragraphs):
            para = paragraph.text
            if len(para.split("\n")) > 1:  # 出现空行等情况？
                for line in para.split():
                    line = line.replace(u'\u3000',u'')
                    if len(line) > 0:
                        paras.append(line)
            else:
                if self.chinese_detection(para):
                    count += 1
                    paras.append(para)

        # 拆分过长的段落:
        temp_paras = []
        for para in paras:
            if len(para)>100:
                temp_sens = re.split(r"([。？！])", para)
                adjust_para = [[]]
                para_len=0
                for sen in temp_sens:
                    if len("".join(adjust_para[-1]))>50 and \
                        adjust_para[-1][-1] in ["。", "？", "！"]:
                        adjust_para.append([])
                    adjust_para[-1].append(sen)
                for sen_list in adjust_para:
                    adjust_sen = "".join(sen_list)
                    if len(adjust_sen)>0:
                        temp_paras.append(adjust_sen)
            elif len(para)>0:
                temp_paras.append(para)
        paras=temp_paras

        final_paras = []
        temp_str = ""
        idx = 0
        print(len(paras)-1)
        while idx < len(paras)-1:
            temp_str += paras[idx]
            if len(temp_str)==0:
                print(paras[idx]+":"+str(len(paras[idx])))
            while len(temp_str) < 50:  # 合并50字以内的段落
                if temp_str[-1] not in ["，","。","？","！","‘","”"]:
                    if idx+1 > len(paras)-1:
                        break
                    else:
                        temp_str += paras[idx+1]
                else:
                    if idx+1 > len(paras)-1:
                        break
                    else:
                        temp_str += "\n" + paras[idx+1]
                idx += 1

            # 若不是结束标点，则再加一句话 TODO：更合理的段落合并
            if len(paras) - 1 > idx+1 and temp_str[-1] not in ["，","。","？","！","‘","”"]:
                temp_str += paras[idx+1]
                idx += 1

            final_paras.append(temp_str)
            temp_str = ""
            idx += 1

        return final_paras


if __name__ == "__main__":
    file_path = "../inputs/test2.docx"
    txtReader = ProcessDocx()
    paragraphs = txtReader.get_paras(file_path)
    print(paragraphs)
