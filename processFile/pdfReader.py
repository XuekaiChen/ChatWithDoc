# -*- coding: utf-8 -*-
# Date       ：2023/5/30
# Author     ：Chen Xuekai
# Description：PDF处理类，包含文本抽取、表格抽取、大纲抽取功能
import os
import pdfplumber
import pandas as pd
from PyPDF2 import PdfReader
from pprint import pprint

"""
功能1、抽取文本
    ·段落自动拆分合并（根据行间距） （由于中英文间距、字体等问题，不便使用自然段缩进识别）
    ·支持用户设置合并行间距（默认则使用自动计算推荐行间距）
    ·可选择页面范围、是否合并跨页内容、是否去除页眉页脚
    ·支持表格内容和文本分离
    ·TODO 设置最小识别字号，避免识别图例等内容
    
功能2、抽取表格
    ·可选择页面范围、是否跨页合并
    ·支持跨多页表格自动合并
    
功能3、抽取大纲
    ·自动按大纲视图识别多级标题
    ·层级式输出章节位置和嵌套关系
"""


class ProcessPdf:
    def __init__(self, header: bool = False, footer: bool = False):
        self.pyPDF2_pdf = None
        self.pdfplumber_pdf = None
        self.header = header
        self.footer = footer

    def _preprocess(self, path, header, footer):
        self._pdfplumber_pdf = pdfplumber.open(path)
        self._min_lineSpace = 30  # 默认的合并行间距
        halve = int(len(self._pdfplumber_pdf.pages) / 2)
        self._longitudinal = [self._pdfplumber_pdf.pages[0].bbox[1], self._pdfplumber_pdf.pages[0].bbox[3]]

        plumber_content = self._pdfplumber_pdf.pages[halve]
        words = plumber_content.extract_words(y_tolerance=2)  # 此处设置tolerance防止页眉页脚有加粗等情况

        # 若有页眉页脚，缩小页面纵向范围
        if header and self._longitudinal[0] < words[0]['bottom']:
            self._longitudinal[0] = words[0]['bottom']
        if footer and self._longitudinal[1] > words[-1]['top']:
            self._longitudinal[1] = words[-1]['top']

        # 推荐tolerance行距
        for i in range(0, len(words) - 1):
            diff = words[i + 1]['top'] - words[i]['top']
            if 15 < diff < self._min_lineSpace:
                self._min_lineSpace = diff
        self._min_lineSpace += 2
        print("默认选择推荐tolerance行距值：", self._min_lineSpace)
        return

    def extract_outline(self, path) -> list:
        f = open(path, 'rb')
        self.pyPDF2_pdf = PdfReader(f)
        text_outline_list = self.pyPDF2_pdf.outline
        return self._read_structure(text_outline_list)

    def _read_structure(self, chapter_list) -> list:
        outline_list = []
        for message in chapter_list:
            # 若为叶子章节，则将title和page加入
            if isinstance(message, dict):
                chapter = {
                    "title": message['/Title'],
                    "page": self.pyPDF2_pdf.get_destination_page_number(message),
                    "subchapter": []
                }
                outline_list.append(chapter)
            else:  # 嵌套了章节
                outline_list[-1]["subchapter"] = self._read_structure(message)
        return outline_list

    def get_paras(self,
                  path: str,
                  page_scope: list = None,
                  line_tolerance: float = None,
                  merge_page_end: bool = True):
        """
        :param path: 文件路径
        :param page_scope: 页面范围(从1开始)，[起始页, 结束页]
        :param line_tolerance: 行距容差，需要合并内容的行距
        :param merge_page_end: 是否拼接上下页段落
        :return: 段落列表，段落页码
        """
        self._preprocess(path, self.header, self.footer)
        if line_tolerance:
            min_lineSpace = line_tolerance
        else:
            min_lineSpace = self._min_lineSpace

        if not page_scope:  # 未指定页面范围
            page_scope = [1, len(self._pdfplumber_pdf.pages)]
        elif len(page_scope) != 2 or page_scope[0] > page_scope[1] or page_scope[0] < 1 or page_scope[1] > len(
                self._pdfplumber_pdf.pages):
            print("指定页面范围有误")
            return []

        output_paragraph = []
        para_page = []
        paragraph = ""
        for page_num in range(page_scope[0] - 1, page_scope[1]):
            # 去除表格部分
            tables = self._pdfplumber_pdf.pages[page_num].find_tables()
            # 获取表格上下界，以得到文本的上下界
            top_bound = [self._longitudinal[0]]
            bottom_bound = []
            for table in tables:
                top_bound.append(table.bbox[3])  # 文字的上边界为表格的下边界
                bottom_bound.append(table.bbox[1])  # 文字的下边界为表格的上边界
            bottom_bound.append(self._longitudinal[1])
            text_scopes = list(zip(top_bound, bottom_bound))

            # 若出现同行表格，则plumber工具无法避开，只能当做文本抽取出来
            if not all(top < bottom for (top, bottom) in text_scopes):
                text_scopes = [(self._longitudinal[0], self._longitudinal[1])]

            # 遍历非表格区域
            for text_scope in text_scopes:
                # 裁剪范围
                scope_tuple = (
                    self._pdfplumber_pdf.pages[page_num].bbox[0],  # x0
                    text_scope[0],  # top
                    self._pdfplumber_pdf.pages[page_num].bbox[2],  # x1
                    text_scope[1]  # bottom
                )
                plumber_content = self._pdfplumber_pdf.pages[page_num].within_bbox(scope_tuple)
                words = plumber_content.extract_words()
                if not words:
                    continue

                # 合并同段落文字
                for i in range(0, len(words) - 1):
                    paragraph += words[i]['text']
                    # 行距超过阈值，则分离段落
                    if words[i + 1]['top'] - words[i]['top'] > min_lineSpace:
                        output_paragraph.append(paragraph)
                        para_page.append(page_num+1)
                        paragraph = ""

                # 单独处理页面最后一行
                if len(words) > 1 and words[-1]['top'] - words[-2]['top'] <= min_lineSpace:
                    paragraph += words[-1]['text']
                    output_paragraph.append(paragraph)
                    para_page.append(page_num + 1)
                    paragraph = ""
                else:  # 最后一行单独成段
                    output_paragraph.append(words[-1]['text'])
                    para_page.append(page_num + 1)

                # 若选择合并跨页内容，则在页面最后分区将output_paragraph末元素转到临时变量
                if merge_page_end and text_scope[1] == self._longitudinal[1]:
                    paragraph = output_paragraph[-1]
                    del output_paragraph[-1]
                    del para_page[-1]

        # 全书扫描结束，添加最后一段
        if paragraph:
            output_paragraph.append(paragraph)
            para_page.append(page_scope[1])

        return output_paragraph, para_page

    # TODO 或许表格能形成Markdown形式加入文本
    def extract_tables(self,
                       path: str,
                       page_scope: list = None,
                       merge_cross_table: bool = True) -> dict:
        """
        :param path: 文件路径
        :param page_scope: 页面范围(从1开始)，[起始页, 结束页]
        :param merge_cross_table: 是否合并跨页表格
        :return:
        """
        self._preprocess(path, self.header, self.footer)
        if not page_scope:  # 未指定页面范围
            page_scope = [1, len(self._pdfplumber_pdf.pages)]
        elif len(page_scope) != 2 or page_scope[0] > page_scope[1] or page_scope[0] < 1 or page_scope[1] > len(
                self._pdfplumber_pdf.pages):
            print("指定页面范围有误")
            return {}

        temp_table = pd.DataFrame([])
        df_tables = []
        table_name_list = []
        for page_num in range(page_scope[0] - 1, page_scope[1]):
            scope_tuple = (
                self._pdfplumber_pdf.pages[page_num].bbox[0],  # x0
                self._longitudinal[0],  # top
                self._pdfplumber_pdf.pages[page_num].bbox[2],  # x1
                self._longitudinal[1]  # bottom
            )
            page = self._pdfplumber_pdf.pages[page_num].within_bbox(scope_tuple)
            tables = page.extract_tables()
            if len(tables) == 0:
                continue
            for table_id, table in enumerate(tables):
                df = pd.DataFrame(table)
                table_name = str(page_num + 1) + "-" + str(table_id + 1)
                # 若不合并跨页表格，则直接输出
                if not merge_cross_table:
                    df_tables.append([df, [table_name]])
                    continue

                # 页首判断逻辑：除页眉外首字符到顶部的距离+容差>=表格首字符到顶部的距离
                if page.bbox[3]-page.chars[0].get('y1')+self._min_lineSpace >= page.find_tables()[table_id].bbox[1]-self._longitudinal[0]:  # 是页首
                    # 与temp合并
                    temp_table = pd.concat([temp_table, df], axis=0)
                    table_name_list.append(table_name)
                    if page.chars[-1].get('y0') >= page.bbox[3]-page.find_tables()[table_id].bbox[3]-self._min_lineSpace:  # 是页尾
                        break  # 跳过本页其他内容，继续拼接下页
                    else:  # 不是页尾，输出temp并清空
                        df_tables.append([temp_table, table_name_list])
                        temp_table = pd.DataFrame([])
                        table_name_list = []
                else:  # 不是页首
                    if not temp_table.empty:  # 若temp有值，先入temp
                        df_tables.append([df, table_name_list])
                        temp_table = pd.DataFrame([])
                    table_name_list = [table_name]
                    if page.chars[-1].get('y0') >= page.bbox[3]-page.find_tables()[table_id].bbox[3]-self._min_lineSpace:  # 是页尾
                        # 存入temp
                        temp_table = pd.concat([temp_table, df], axis=0)
                    else:  # 不是页尾，输出
                        df_tables.append([df, table_name_list])
                        temp_table = pd.DataFrame([])
                        table_name_list = []

        # 遍历结束，temp输出
        if not temp_table.empty:
            df_tables.append([temp_table, table_name_list])

        # 合并table_name，形成字典{table_name:df_table}输出
        table_dict = {}
        for table_ele in df_tables:
            name = "_".join(table_ele[1])
            table_dict[name] = table_ele[0]

        return table_dict


if __name__ == "__main__":
    pdfReader = ProcessPdf(header=True, footer=True)
    file_path = "../inputs/景杰生物招股说明书.pdf"
    outlines = pdfReader.extract_outline(file_path)
    paragraphs = pdfReader.get_paras(file_path, merge_page_end=False)
    for idx, i in enumerate(paragraphs):
        print(idx, "\t", i)


