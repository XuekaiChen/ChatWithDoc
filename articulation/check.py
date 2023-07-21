# -*- coding: utf-8 -*-
# Date       ：2023/7/7
# Author     ：Chen Xuekai
# Description：返回：跨表勾稽json、表内勾稽json、文表勾稽json、正确json
import os
import re
import time
import pandas as pd
import fitz
import pdfplumber
from articulation.extract_rule import get_rule
from articulation.data2json import excels2json
from articulation.pdf_tables_extract import extract_all_table
from articulation.cross_judge import precheck_and_get_dict, judge_from_rule
from articulation.inner_judge import inner_check
from articulation.text_judge import text_check
from articulation.util import get_pdf


def find_error_value(table, field_name, error_idx):
    for row in table:
        if row[0] == field_name:
            return row[error_idx]


# 将输出字典整理为用户可读形式，目前支持inner_result
def transform_inner_output(output_dict):
    output = ""
    # 获取页码
    uptable_page = output_dict['上勾稽表字段']['所在表格'].split('-')[0]
    downtable_page = [i['所在表格'].split('-')[0] for i in output_dict['下勾稽表字段']]
    downtable_page.append(uptable_page)
    page_nums = [int(i)+1 for i in downtable_page]
    page_nums.sort()
    if len(set(page_nums)) > 1:
        output += f"第{page_nums[0]} ~ {page_nums[-1]}页\n"
    else:
        output += f"第{page_nums[0]}页\n"
    # 提取规则
    output += f"规则：{output_dict['规则']}\n"
    # 显示错误列号
    error_column = [i+1 for i in output_dict['上勾稽表字段']['错误列号']]
    for idx, error_ele in enumerate(error_column):
        output += f"第{error_ele}列错误："
        # 显示数值计算
        up_num = find_error_value(output_dict['表格内容'], output_dict['上勾稽表字段']['字段名称'], error_ele)  # int
        down_nums = [find_error_value(output_dict['表格内容'], i['字段名称'], error_ele) for i in output_dict['下勾稽表字段']]  # list_int
        operators = re.findall(r'[+\-*/]', output_dict['规则'])
        output += f"{up_num} ≠ {down_nums[0]} "
        if len(operators) != len(down_nums)-1:
            raise Exception("规则提取错误")
        for i in range(len(operators)):
            output += f"{operators[i]} {down_nums[i+1]} "
        # 显示差值
        output = output[:-1] + f"\n差值：{output_dict['差值'][idx]}\n"
    output += "\n"
    return output


def transfrom_cross_output(output_dict):
    output = ""
    uptable_page = int(output_dict['上勾稽表']['表格编号'].split('-')[0])+1
    output += f"上勾稽表：第{uptable_page}页\n"
    downtable_page = [i['表格编号'].split('-')[0] for i in output_dict['下勾稽表']]
    page_nums = [int(i) + 1 for i in downtable_page]
    page_nums.sort()
    if len(set(page_nums)) > 1:
        output += f"下勾稽表：第{page_nums[0]} ~ {page_nums[-1]}页\n"
    else:
        output += f"下勾稽表：第{page_nums[0]}页\n"
    # 提取规则
    output += f"规则：{output_dict['规则']}\n"
    # 显示错误列号
    error_column = [i + 1 for i in output_dict['上勾稽表']['错误列号']]
    for idx, error_ele in enumerate(error_column):
        output += f"第{error_ele}列错误："
        # 显示数值计算
        up_num = find_error_value(output_dict['上勾稽表']['表格内容'], output_dict['上勾稽表']['字段名称'], error_ele)  # int
        down_nums = [find_error_value(i['表格内容'], i['字段名称'], error_ele) for i in output_dict['下勾稽表']]  # list_int
        operators = re.findall(r'[+\-*/]', output_dict['规则'])
        output += f"{up_num} ≠ {down_nums[0]} "
        if len(operators) != len(down_nums) - 1:
            raise Exception("规则提取错误")
        for i in range(len(operators)):
            output += f"{operators[i]} {down_nums[i + 1]} "
        # 显示差值
        output = output[:-1] + f"\n差值：{output_dict['差值'][idx]}\n"
    output += "\n"
    return output


def transform_text_output(output_dict):
    output = ""
    # 提取文本内容
    output += f"规则：{output_dict['规则']}\n"
    pages = [int(i['页码'])+1 for i in output_dict['关联文本']['位置']]
    pages.sort()
    if len(set(pages)) > 1:
        output += f"关联文本：第{pages[0]} ~ {pages[-1]}页，{output_dict['关联文本']['内容值']}\n"
    else:
        output += f"关联文本：第{pages[0]}页，{output_dict['关联文本']['内容值']}\n"
    for table_num in range(len(output_dict['勾稽表'])):
        table_page = int(output_dict['勾稽表'][table_num]['表格编号'].split('-')[0]) + 1
        output += f"勾稽表：第{table_page}页\n"
        # 显示错误列号
        error_column = [i + 1 for i in output_dict['勾稽表'][table_num]['错误列号']]
        for idx, error_ele in enumerate(error_column):
            output += f"第{error_ele}列错误："
            # 显示数值计算
            text_item = output_dict['关联文本']['数值列表'][error_ele-1]
            table_item = find_error_value(output_dict['勾稽表'][table_num]['表格内容'], output_dict['勾稽表'][table_num]['字段名称'], error_ele)  # int
            output += f"{text_item} ≠ {table_item}\n"
            # 显示差值
            output += f"差值：{output_dict['差值'][idx]}\n"
    output += "\n"
    return output


class Articulation_check:
    def __init__(self, config):
        self.json_data = None
        self.table_dict = None
        self.pdf = None
        self.doc = None
        self.config = config
        self.rule_dict = get_rule(config["articulation_rule"])

    def extract_table(self, filename):
        self.doc = fitz.open(filename)
        self.pdf = pdfplumber.open(filename)
        self.table_dict = extract_all_table(pdf=self.pdf)
        self.json_data = excels2json(table_dict=self.table_dict)
        print("**************************** 表格抽取完毕！****************************")

    def check(self, file):
        # file_path = file.name
        file_path = file
        # 若文件为空，则提示上传
        if file_path == "":
            return "请先上传文档", "请先上传文档"

        # 若文件md5存在，则读取校验json并返回

        # 其他，读取文件内容，开始勾稽关系校验
        cross_result = []
        inner_result = []
        text_result = []
        pdf_out_path = "hightlight.pdf"
        correct_dict = {"跨表勾稽": [], "表内勾稽": [], "文表勾稽": []}

        print("----------------------同名字段跨表校验-------------------------")
        json_data2, inverted_list, cross_result, correct_dict = precheck_and_get_dict(
            chart_data=self.json_data,
            pdf=self.pdf,
            doc=self.doc,
            cross_result=cross_result,
            correct_dict=correct_dict
        )

        print("----------------------规则校验-------------------------")
        cross_result, inner_result, correct_dict = judge_from_rule(
            chart_data2=json_data2,
            table_dict=self.table_dict,
            rules=self.rule_dict,
            pdf=self.pdf,
            doc=self.doc,
            inverted_list=inverted_list,
            cross_result=cross_result,
            inner_result=inner_result,
            correct_dict=correct_dict
        )

        print("----------------------表内校验-------------------------")
        inner_result, correct_dict = inner_check(
            chart_data=self.json_data,
            table_dict=self.table_dict,
            pdf=self.pdf,
            doc=self.doc,
            inner_result=inner_result,
            correct_dict=correct_dict
        )

        print("----------------------文表校验-------------------------")
        text_result, correct_dict = text_check(
            chart_data=json_data2,
            pdf=self.pdf,
            doc=self.doc,
            inverted_list=inverted_list,
            text_result=text_result,
            correct_dict=correct_dict
        )
        correct_inner = "\n\n".join(correct_dict['表内勾稽'])  # TODO 提取页码
        correct_cross = "\n\n".join(correct_dict['跨表勾稽'])
        correct_text = "\n\n".join(correct_dict['文表勾稽'])

        print("----------------------勾稽关系校验完毕！------------------------")
        self.doc.save(pdf_out_path)
        highlight_html = get_pdf(pdf_out_path, self.config['pdf_url'])

        error_inner = ""
        error_cross = ""
        error_text = ""
        for error_item in inner_result:
            error_inner += transform_inner_output(error_item)
        for error_item in cross_result:
            error_cross += transfrom_cross_output(error_item)
        for error_item in text_result:
            error_text += transform_text_output(error_item)

        if error_inner == "":
            error_inner = "无表内勾稽错误！"
        if error_cross == "":
            error_cross = "无跨表勾稽错误！"
        if error_text == "":
            error_text = "无文表勾稽错误！"

        return correct_inner, correct_cross, correct_text, error_inner, error_cross, error_text, highlight_html


if __name__ == "__main__":
    import yaml
    filename = "/data/chenxuekai/ChatFin/inputs/jingjie.pdf"
    with open("/data/chenxuekai/ChatFin/config.yaml") as f:
        cfg = yaml.safe_load(f)
    checker = Articulation_check(cfg)
    checker.extract_table(filename)
    _,_,_,_,_,_=checker.check(filename)

