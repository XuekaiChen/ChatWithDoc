# -*- coding: utf-8 -*-
# Date        : 2023/2/21
# Author      : Chen Xuekai
# Description : 各校验代码的公共函数，包括数值比对、定位等
import re
import fitz
import json
import requests

# 转为float
def to_float_list(l):
    return [float(i) for i in l]


# 判断是否是数字
def is_number(target_str):
    try:
        float(target_str)
        return True
    except:
        pass
    if target_str.isdecimal():
        return True
    return False


# 判断某数组是否都是数字
def is_number_list(l):
    for i in l:
        if not is_number(i):
            return False
    return True


# 两个列表元素逐个对比，返回错误索引列表
def get_error_list(list1, list2) -> dict:
    temp_error = {}  # {错误列号：差值}
    error_dict = {}
    magnitude = 1  # 量级标注，解决万元问题
    for idx, (i, j) in enumerate(zip(list1, list2)):
        if round(i, 2) == round(j, 2):
            magnitude = 1  # 数字列表量级差是固定的，只要确定一次就可以使用
        elif round(i, 2) == round(j / 10000, 2):
            magnitude = 10000
        elif round(i / 10000, 2) == round(j, 2):
            magnitude = 0.0001
        else:
            temp_error[idx] = [i, j]
    # 按量级处理差值问题
    for key, value in temp_error.items():
        if magnitude == 10000:  # 避免较小数乘10000后出问题
            diff = abs(value[0] - value[1] * 0.0001)
        else:
            diff = abs(value[0] * magnitude - value[1])
        if diff >= 0.02:
            error_dict[key] = round(diff, 2)
    return error_dict


# 正确匹配则返回错误列号列表，无法匹配则返回“字段匹配错误”字符串
def equal_check(list1, list2):
    # 解决穿插百分比的列表
    if len(list1) == len(list2) * 2:
        list1 = list1[0:-1:2]
    elif len(list1) == len(list2) / 2:
        list2 = list2[0:-1:2]
    # 等长列表判定元素
    if len(list1) == len(list2):
        error_list1 = get_error_list(list1, list2)
        error_list2 = get_error_list(list1[::-1], list2)  # 考虑文表勾稽经常有反着说的
        error_list = min([error_list1, error_list2], key=len)
        if (len(error_list) != len(list1)) and (0 not in list1) and (0 not in list2):
            if error_list == error_list2:
                return error_list, True  # 第二个参数为是否翻转
            else:
                return error_list, False
        else:  # 全都不一样说明匹配错误
            return "字段匹配错误", False
    else:
        return "字段匹配错误", False


# 给出文本，返回其在文档中的位置
def locate_txt_info(pdf, doc, sentence):
    result = []
    # 因为考虑到跨页问题，在抽取时合并了跨页内容，但定位时不能合并，只能从全部pdf页找整句话内容，此处可能可以优化
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = pdf.pages[page_num].extract_text().replace("\n", "")
        if re.findall(sentence, text):  # 首先确定字符肯定在当前页面中  TODO：如果文字段跨页就又不行了
            # 由于直接search会因为各种格式不一致问题而匹配不上，只能不断按最大长度切分匹配  TODO：出现短句转行问题（如公司\n税收优惠金额）
            head = 0
            tail = len(sentence)
            while head != tail:
                search_part = pdf.pages[page_num].search(sentence[head:tail])
                if search_part:  # 搜寻到部分字符串，将四元组加入位置列表
                    for out in search_part:
                        bbox = fitz.Rect(out['x0'], out['top'], out['x1'], out['bottom'])
                        page.add_highlight_annot(bbox)
                        location_tetrad = {
                            "页码": page_num,  # 文件页脚内写的页码
                            "x0": out['x0'],
                            "top": out['top'],
                            "x1": out['x1'],
                            "bottom": out['bottom']
                        }
                        result.append(location_tetrad)
                    head = tail
                    tail = len(sentence)
                    continue
                tail -= 1
    return result


# 给出字段信息，返回其在文档中的位置
# 外层判断，若error_col为0 名称为正确，否则为错误
# 文表、跨表勾稽在外层遍历所有表，单列为一个正确/错误项
# field_list, col_num_list, error_col_list三者长度相同，为字段中元素个数
def locate_cross_chart_info(pdf, doc, chart_name, field_list, col_num_list, error_cols_list):
    """
    输出样例
    result = [
    {
        "表格编号": "187-1",  //此处表名为单表
        "表格内容": [],
        "字段名称": "所得税优惠金额",
        "错误列号": [],
        "位置": {
            "x0": 278.92200233333335,
            "y0": 535.2699844444445,
            "x1": 355.24378055555553,
            "y1": 555.9785714285712
        }     //为整行坐标  TODO 问上交所需不需要把位置按列表给出，里面是错误单元格四元组or正确整行四元组
    }, {},...{}
    ]
    """
    result_list = []
    for subtable_name in chart_name.split("_"):
        # 根据表名提取表格及表格属性
        page_num, table_num = int(subtable_name.split("-")[0]), int(subtable_name.split("-")[1]) - 1
        table, table_attr = pdf.pages[page_num].extract_tables()[table_num], pdf.pages[page_num].find_tables()[table_num]
        # 遍历每个待搜寻字段
        for field_name, col_num, error_cols in zip(field_list, col_num_list, error_cols_list):
            # 遍历表格每一行
            for row_num in range(len(table)):
                if (table[row_num][0] is not None) and (table[row_num][0].replace("\n", "") == field_name) \
                        and (col_num == len(table[row_num])):  # 字段在该行
                    loc_tuple = table_attr.rows[row_num].bbox
                    bbox = fitz.Rect(loc_tuple[0], loc_tuple[1], loc_tuple[2], loc_tuple[3])
                    doc[page_num].add_highlight_annot(bbox)  # highlight
                    json_result = {
                        "表格编号": subtable_name,
                        "表格内容": table,
                        "字段名称": field_name,
                        "错误列号": error_cols,
                        "位置": {
                            "x0": loc_tuple[0],
                            "top": loc_tuple[1],
                            "x1": loc_tuple[2],
                            "bottom": loc_tuple[3]
                        }
                    }
                    result_list.append(json_result)
    return result_list


# 输出结构与locate_cross_chart_info()不同，定位方式完全相同
def locate_inner_chart_info(pdf, doc, chart_name, field_list, col_num_list, error_cols_list):
    """
    输出样例
    result = [
      {
        "所在表格": "217-2",
        "字段名称": "资产总计",
        "错误列号": [],
        "位置": {
          "x0": 60.28127999999997,
          "top": 731.3795400000001,
          "x1": 535.1512000000003,
          "bottom": 752.1085714285713
        }
      }
    ],
    """
    result_list = []
    for subtable_name in chart_name.split("_"):
        # 根据表名提取表格及表格属性
        page_num, table_num = int(subtable_name.split("-")[0]), int(subtable_name.split("-")[1]) - 1
        table, table_attr = pdf.pages[page_num].extract_tables()[table_num], pdf.pages[page_num].find_tables()[
            table_num]
        # 遍历每个待搜寻字段
        for field_name, col_num, error_cols in zip(field_list, col_num_list, error_cols_list):
            # 遍历表格每一行
            for row_num in range(len(table)):
                if (table[row_num][0] is not None) and (table[row_num][0].replace("\n", "") == field_name) \
                        and (col_num == len(table[row_num])):  # 字段在该行
                    loc_tuple = table_attr.rows[row_num].bbox
                    bbox = fitz.Rect(loc_tuple[0], loc_tuple[1], loc_tuple[2], loc_tuple[3])
                    doc[page_num].add_highlight_annot(bbox)  # highlight
                    json_result = {
                        "所在表格": subtable_name,
                        "字段名称": field_name,
                        "错误列号": error_cols,
                        "位置": {
                            "x0": loc_tuple[0],
                            "top": loc_tuple[1],
                            "x1": loc_tuple[2],
                            "bottom": loc_tuple[3]
                        }
                    }
                    result_list.append(json_result)
    return result_list


def get_pdf(pdf_path, target_url):
    data = {"pdf_filename": pdf_path}
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    headers = {'Content-Type': 'application/json'}
    response = requests.request("post", target_url, headers=headers, data=payload)
    result = json.loads(response.text)["out_html"]
    return result
