# -*- coding: utf-8 -*-
# Date       ：2023/1/20
# Author     ：Chen Xuekai
# Description：按页码顺序抽取招股书pdf中的表格，跨页表格可合并

import os
import json
import pdfplumber
import pandas as pd


def extract_all_table(pdf, out_path=""):
    temp_table = None
    df_tables = []
    table_name = []
    for page_index, page in enumerate(pdf.pages):
        if len(page.extract_tables()) == 0:
            continue
        num_table = len(page.extract_tables())
        for table_id in range(num_table):
            table = page.extract_tables()[table_id]
            if temp_table is not None and table_id == 0:  # 上页有可能没结束的表
                if page.bbox[3]-page.find_tables()[table_id].bbox[1] + 30 >= page.chars[0].get('y1'):  # 该表是页首（-30代表去掉空隙，是针对招股书pdf设计的特定值）
                    # df = pd.DataFrame(table[1:], columns=table[0])  # TODO: 判断是否有表头，有的话可能要合并表头
                    # 与temp拼合
                    df = pd.DataFrame(table)
                    temp_table = pd.concat([temp_table, df], axis=0)
                    table_name.append(str(page_index) + "-" + str(table_id + 1))
                    if page.chars[-1].get('y0') < page.bbox[3] - page.find_tables()[table_id].bbox[3]:  # 该表不是页尾，结束拼接，加入table_list，temp置空
                        df_tables.append([temp_table, table_name])
                        temp_table = None
                        table_name = []
                    else:  # 该表是页尾，继续拼接下一页表格
                        break
                else:  # 该表不是页首，上页页尾表格结束，加入table_list
                    df_tables.append([temp_table, table_name])
                    temp_table = None
                    table_name = []
                    if page.chars[-1].get('y0') < page.bbox[3] - page.find_tables()[table_id].bbox[3]:  # 该表不是页尾，直接加入table_list
                        df = pd.DataFrame(table)
                        table_name = [str(page_index) + "-" + str(table_id + 1)]
                        df_tables.append([df, table_name])
                        table_name = []
                    else:  # 该表是页尾，存入temp
                        temp_table = pd.DataFrame(table)
                        table_name.append(str(page_index) + "-" + str(table_id + 1))
            else:  # temp无值（上个表页尾不是表）
                if page.chars[-1].get('y0') < page.bbox[3] - page.find_tables()[table_id].bbox[3]:  # 该表不是页尾，直接加入table_list
                    df = pd.DataFrame(table)
                    table_name = [str(page_index) + "-" + str(table_id + 1)]
                    df_tables.append([df, table_name])
                    table_name = []
                else:  # 该表是页尾，存入temp
                    temp_table = pd.DataFrame(table)
                    table_name.append(str(page_index) + "-" + str(table_id + 1))

    table_dict = {}
    for table_ele in df_tables:
        name = "_".join(table_ele[1])
        table_dict[name] = table_ele[0].values.tolist()

    if out_path != "":
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(table_dict, f, ensure_ascii=False)

    return table_dict


if __name__ == "__main__":
    import time
    start = time.time()
    path = "预披露 景杰生物 2022-12-02  1-1 招股说明书_景杰生物.pdf"
    pdf = pdfplumber.open(path)
    out_path = "table_dict2.json"
    table_dic = extract_all_table(pdf, out_path)
    pdf.close()
    print("抽取表格用时：{:.2f}秒".format(time.time() - start))
    print(list(table_dic.items())[:5])
