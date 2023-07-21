# -*- coding: utf-8 -*-
# Date       ：2023/2/20
# Author     ：Chen Xuekai
# Description：逐表格进行表内勾稽校验

import json
import fitz
import pdfplumber
import numpy as np
from articulation.util import equal_check, locate_inner_chart_info


def iseverylist_leneaual(list_a):
    for i in range(len(list_a) - 1):
        if len(list_a[i]) != len(list_a[i + 1]):
            return False
    return True


def inner_check(chart_data, table_dict, pdf, doc, inner_result, correct_dict):
    for chart_name, chart in chart_data.items():
        # 表内字段名称列表
        field_list = [list(i.keys())[0] for i in chart]
        # 判定所有数字列表长度是否相等，获取数字列表长度
        field_value = [list(i.values())[0] for i in chart]
        if not iseverylist_leneaual(field_value):
            continue
        else:
            value_len = len(field_value[0])

        # 二维数字列表
        value_list = list(map(lambda x: [0] * value_len if x == [] else x, field_value))
        indexlist = [-1]
        for idx, field_name in enumerate(field_list):
            if '合计' in field_name or "小计" in field_name:
                indexlist.append(idx)
        if indexlist != [-1]:
            for sum_row_idx in range(len(indexlist)-1):
                up_total = value_list[indexlist[sum_row_idx + 1]]  # 合计的数值
                start_index = indexlist[sum_row_idx] + 1
                end_index = indexlist[sum_row_idx + 1]
                if start_index >= end_index:  # 两行紧挨着出现合计的情况
                    continue
                down_total = np.sum(np.array(value_list[start_index:end_index]), axis=0)
                check_result, _ = equal_check(up_total, down_total)
                if check_result != "字段匹配错误":
                    error_col = list(check_result.keys())
                    diff_value = list(check_result.values())
                    if len(error_col) >= 1 / 2 * min(len(up_total), len(down_total)):  # 错误过多，说明没正确匹配
                        continue
                    up_field = field_list[indexlist[sum_row_idx + 1]]
                    down_field_list = field_list[indexlist[sum_row_idx] + 1:indexlist[sum_row_idx + 1]]
                    down_field = ' + '.join(down_field_list)
                    if not check_result:  # check_result为空表示校验正确
                        correct_out = f"校验正确：{up_field} = {down_field}"
                        correct_dict['表内勾稽'].append(correct_out)
                        print(correct_out)
                        continue

                    print(chart_name)
                    print(f"规则：{up_field} = {down_field}")
                    print(up_total)
                    print(down_total)
                    print("出错列：", error_col)
                    print("差值：", diff_value)
                    print()
                    # 定位
                    up_table_info = locate_inner_chart_info(pdf, doc, chart_name, [up_field], [len(up_total) + 1], [error_col])
                    col_len_list = [len(down_total) + 1 for i in range(len(down_field_list))]  # 所有每行的长度列表
                    error_col_list = [error_col for i in range(len(down_field_list))]  # 每行的错误列
                    down_table_info = locate_inner_chart_info(pdf, doc, chart_name, down_field_list, col_len_list, error_col_list)
                    if (not up_table_info) or (not down_table_info):
                        continue
                    json_item = {
                        "规则": up_field + " = " + down_field,
                        "表格编号": chart_name,
                        "表格内容": table_dict[chart_name],
                        "上勾稽表字段": up_table_info[0],
                        "下勾稽表字段": down_table_info,
                        "差值": diff_value
                    }
                    inner_result.append(json_item)

    return inner_result, correct_dict


if __name__ == "__main__":
    import time
    print("正在进行表内勾稽关系校验......")
    start = time.time()
    path = "预披露 景杰生物 2022-12-02  1-1 招股说明书_景杰生物.pdf"
    field_data_path = 'table_content.json'
    table_dict_path = 'table_dict.json'
    highlight_pdf = "Articulation_out/inner_highlight.pdf"
    output_file = "Articulation_out/try_inner.json"
    doc = fitz.open(path)
    pdf = pdfplumber.open(path)
    inner_result = []
    with open(field_data_path, 'r', encoding='utf-8') as fp:
        json_data = json.load(fp)
    with open(table_dict_path, 'r', encoding='utf-8') as fp:
        table_dict = json.load(fp)

    # 校验
    inner_result = inner_check(json_data, table_dict, pdf, doc, inner_result)

    # 存储
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(inner_result, f, ensure_ascii=False)
    doc.save(highlight_pdf)
    pdf.close()
    doc.close()

    print("表内勾稽关系校验完毕，用时：{:.2f}秒".format(time.time() - start))
