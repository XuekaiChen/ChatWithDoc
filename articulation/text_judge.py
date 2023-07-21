# -*- coding: utf-8 -*-
# Date       ：2023/2/17
# Author     ：Chen Xuekai
# Description：提取校验文本，搜寻表格中校验字段，进行文表勾稽校验

import pdfplumber
import re
import json
import fitz
import difflib
from articulation.util import to_float_list, is_number_list, equal_check, locate_cross_chart_info, locate_txt_info


punctuation = '[\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\uff1f\u300a\u300b]'
float_pattern = "[-+]?[0-9]*\.?[0-9]+"


def match_strings(a: list, b: list):
    matches = []
    # 依次找出b中与a每个元素最相似的元素
    for string1 in a:
        best_match = difflib.get_close_matches(string1, b, n=1)
        if best_match:
            matches.append((string1, best_match[0]))
    return matches


def get_all_field(json_data_path):
    with open(json_data_path, 'r', encoding='utf-8') as fp:
        json_data = json.load(fp)
    json_data2 = {}
    all_field = list(json_data.values())

    # 构建倒排表 {字段：所属表格}
    inverted_list = {}
    for table_name, fields in json_data.items():
        if fields is None:  # 过滤fields为空的表
            continue
        for fields_name in fields.keys():
            if fields_name == "":  # 过滤字段为空的项
                continue
            try:
                inverted_list[fields_name].append(table_name)
            except:
                inverted_list[fields_name] = [table_name]
    # 合并大字典，{所有字段：数值列表}
    for field in all_field:
        if field is None:  # 过滤fields为空的表  TODO 目前没有field为空的表
            continue
        for field_name, field_num_list in field.items():
            if field_name == "":  # 过滤字段为空的项  TODO 目前没有字段为空的项
                continue
            # 去除非数字或全0列表 TODO 全0列表是否去除
            if not is_number_list(field_num_list) or all(i == 0.0 for i in field_num_list):
                continue
            if field_name not in json_data2:
                json_data2[field_name] = [field_num_list]
            else:
                json_data2[field_name].append(field_num_list)
    # print('data2\n', json_data2)
    return json_data2, inverted_list


# 提取页面中的文本待校验项
def extract_unverified_text(pdf):
    # 读取pdf内容，合并到一个变量中
    all_text = ""
    for page in pdf.pages[1:]:
        text = page.extract_text().strip()
        text = text[text.find("\n") + 1:text.rfind("\n")]  # 去除页眉和页尾
        all_text += text

    # 以“分别为”作为关键字，提取文本中待验证的数字序列
    word_articulation_dict = {}
    for target in re.finditer("分别为", all_text):
        # 提取“分别为“前面字段作为键
        field_key = re.split(punctuation, all_text[:target.start()])[-1].replace("\n", "")
        # 提取“分别为”后面数字列表作为值  TODO：解决带万元问题
        field_value = re.split(punctuation, all_text[target.end():])[0].replace("\n", "")
        # 提取整句话，便于定位
        sentence = field_key + "分别为" + field_value
        # 格式规范化，数字化为列表形式
        field_key, field_value = field_key.strip(), field_value.strip()
        field_value = to_float_list(re.findall(float_pattern, field_value.replace(",", "")))
        # 去除脏数据，加入字典
        if not (field_key == "" or field_value == []):
            word_articulation_dict[field_key] = {"数字列表": field_value, "整句话": sentence}
    # print(list(word_articulation_dict.items())[:10])
    return word_articulation_dict


def check_word_chart(pdf, doc, word_dict, chart_dict, match_list, inverted_list, result_list, correct_dict):
    for matches in match_list:
        if "公司递延所得税资产" == matches[0]:
            print("here")
        txt_num_list = word_dict[matches[0]]["数字列表"]
        chart_num_list_list = chart_dict[matches[1]]
        for chart_num_list in chart_num_list_list:
            # 勾稽校验
            check_result, reverse = equal_check(txt_num_list, chart_num_list)
            if check_result != "字段匹配错误":  # 只对正确匹配到内容的字段进行定位
                error_col = list(check_result.keys())
                diff_value = list(check_result.values())
                if len(error_col) > 1 / 2 * min(len(txt_num_list), len(chart_num_list)):  # 错误过多，说明没正确匹配
                    continue
                if not check_result:  # check_result为空表示校验正确
                    correct_out = f"校验正确：{matches[0]} = {matches[1]}"
                    correct_dict['文表勾稽'].append(correct_out)
                    print(correct_out)
                    continue

                print(f"规则：{matches[0]} = {matches[1]}")
                print(txt_num_list)
                print(chart_num_list)
                print("出错列：", error_col)
                print("差值：", diff_value)
                print()

                # 在文本中定位内容
                sentence = word_dict[matches[0]]["整句话"]
                text_location = locate_txt_info(pdf, doc, sentence)  # 元素为json的列表

                # 在表格中定位内容
                chart_json_list = []
                for table_name in inverted_list[matches[1]]:
                    table_info = locate_cross_chart_info(pdf, doc, table_name, [matches[1]], [len(chart_num_list) + 1], [error_col])
                    if not table_info:
                        continue
                    chart_json_list.append(table_info[0])

                # 加入列表项
                output_item = {
                    "规则": matches[0] + " = " + matches[1],
                    "关联文本": {
                        "内容值": sentence,
                        "数值列表": txt_num_list[::-1] if reverse else txt_num_list,
                        "位置": text_location
                    },
                    "勾稽表": chart_json_list,
                    "差值": diff_value
                }
                result_list.append(output_item)

    return result_list, correct_dict


def text_check(chart_data, pdf, doc, inverted_list, text_result, correct_dict):
    text_data = extract_unverified_text(pdf)
    best_matches = match_strings(list(text_data.keys()), list(chart_data.keys()))
    text_result, correct_dict = check_word_chart(pdf, doc, text_data, chart_data, best_matches, inverted_list, text_result, correct_dict)
    return text_result, correct_dict


if __name__ == "__main__":
    import time
    print("正在进行文表勾稽关系校验......")
    start = time.time()
    path = "预披露 景杰生物 2022-12-02  1-1 招股说明书_景杰生物.pdf"
    field_data_path = 'table_content.json'
    highlight_pdf = "Articulation_out/text_highlight.pdf"
    output_file = "Articulation_out/try_text.json"
    text_result = []
    doc = fitz.open(path)
    pdf = pdfplumber.open(path)

    # 校验
    chart_data, inverted_list = get_all_field(field_data_path)
    text_result = text_check(chart_data, pdf, doc, inverted_list, text_result)

    # 存储
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(text_result, f, ensure_ascii=False)
    doc.save(highlight_pdf)
    pdf.close()
    doc.close()

    print("文表勾稽关系校验完毕，用时：{:.2f}秒".format(time.time() - start))

