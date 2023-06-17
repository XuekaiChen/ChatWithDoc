# -*- coding: utf-8 -*-
# Date       ：2023/6/13
# Author     ：Chen Xuekai
# Description：
import math

"""
读取txt文件，并进行处理，使txt文件转化为段落的txt
"""


class ProcessTxt:
    def __init__(self):
        pass

    # 将文本整合成段落
    def _to_paras(self, lines):
        line_length_list = list(map(lambda x: len(x), lines))
        sort_length_list = line_length_list.copy()
        sort_length_list.sort(reverse=True)
        # 计算文本是否自动分行，如果自动换行
        mid_length = sort_length_list[math.floor(0.5 * len(sort_length_list))]
        paras = []
        if len(lines) < 2:
            paras = lines
        elif mid_length > 0.8 * sort_length_list[0]:
            full_length = mid_length  #  将中间的长度作为判断是否段尾的判断标准
            paras = [lines[0]]
            for i in range(1, len(lines)):
                # 整合段落
                if lines[i].startswith(" ") or len(lines[i - 1]) < mid_length:
                    paras.append(lines[i])
                else:
                    paras[-1] = paras[-1] + lines[i].strip()
        else:
            paras = lines
        # 去除空段落
        paras = [x.strip() for x in paras if x.strip() != '']
        return paras

    def get_paras(self, path):
        file = open(path, 'r')
        # 读取原始txt
        lines = []
        for line in file:
            lines.append(line)
        # 整理成为段落
        paras = self._to_paras(lines)
        return paras


if __name__ == "__main__":
    file_path = "../inputs/requirements.txt"
    txtReader = ProcessTxt()
    paragraphs = txtReader.get_paras(file_path)
    for idx, i in enumerate(paragraphs):
        print(idx, "\t", i)
