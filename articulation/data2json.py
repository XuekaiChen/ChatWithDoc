# -*- coding: utf-8 -*-
# Date       ：2023/3/9
# Author     ：Chen Xuekai
# Description：
import math
from functools import reduce
import json
from articulation.util import is_number, is_number_list


def getTitle(inloc, Elecount, list1, row):
    title_list = []
    for j in range(inloc + 1, len(list1[0])):
        if list1[0][inloc+1] is None:
            list1[0][inloc+1] = ""
        if isinstance(list1[0][j], float):
            if math.isnan(list1[0][j]):
                list1[0][j] = ""
        if list1[0][j] == "" or list1[0][j] is None:
            list1[0][j] = list1[0][j - 1]

    for j in range(inloc + 1, len(row)):
        titley = ''
        for x in range(0, Elecount + 1):
            titley = titley + str(list1[x][j])
            titley = titley.replace('\n', '')
        title_list.append(titley)
    return title_list


def judge_unit(table_list):
    last = table_list[0][-1]
    flag = True
    for i in table_list[0][0:-1]:
        if i is not None:
            flag = False
    if flag:
        table_list.pop(0)
    if type(last) == str:
        if last[0:3] == '单位：':
            table_list.pop(0)
    return table_list


def excels2json(table_dict, out_json=False):
    # 将所有表格以行名为索引记录到字典里，输出json文件
    data_all = {}
    for table_name, table in table_dict.items():
        data_excel = []
        a = -1
        Elecount = 0
        inlocList = []
        flag = True
        table = judge_unit(table)
        for row in table:  # 格式处理
            a = a + 1
            if a == 0:
                title = str(row[0])
                continue
            else:
                if row[0] == "" or row[0] is None:
                    row[0] = table[a - 1][0]
                elif row[0] is not None and '其中' in row[0]:
                    continue
                if flag:
                    if str(row[0]) == title and a + 1 < len(table) and str(table[a + 1][0]) != title and str(
                            table[a - 1][0]) == title:
                        Elecount = Elecount + 1
                    else:
                        flag = False
            if any(row[1:]) is False:  # 去掉数字列表全为0的项
                continue
            if type(row[0]) == str:
                row[0] = row[0].replace('\n', '')
            j = len(row) - 1
            while j > 0:
                if not row[j]:
                    row[j] = 0
                if type(row[j]) == str:
                    row[j] = row[j].replace(',', '')
                if row[j] == '未披露':
                    row[j] = float(-1)
                if row[j] == '-':
                    row[j] = 0
                if is_number(row[j]):
                    row[j] = float(row[j])
                    if math.isnan(row[j]):
                        row[j] = ""
                        continue
                j = j - 1
            inloc = 0
            while inloc + 1 < len(row) and row[inloc + 1] != '' and row[inloc + 1] != '-' and type(
                    row[inloc + 1]) == str:
                inloc = inloc + 1
            if inloc == len(row) - 1:
                continue
            if inloc > 0:
                row[inloc] = reduce(lambda x, y: str(x) + str(y), row[0:inloc + 1])
                row[inloc] = row[inloc].replace('\n', '')
            if isinstance(row[inloc], str) and is_number_list(row[inloc + 1:len(row)]):
                data_excel.append({row[inloc]: row[inloc + 1:len(row)]})
                inlocList.append(inloc)

        if data_excel:
            data_excel.append({"title": getTitle(min(inlocList), Elecount, table, row)})
            data_all[table_name] = data_excel

    if out_json:
        with open(out_json, 'w+', encoding='utf-8') as fp:
            json.dump(data_all, fp, indent=2, ensure_ascii=False)

    return data_all


if __name__ == "__main__":
    table_dict_path = "table_dict.json"
    with open(table_dict_path, 'r', encoding='utf8') as fp:
        table_dict = json.load(fp)
    out_json_path = "table_content_sample.json"
    json_data = excels2json(table_dict, out_json_path)
    print(json_data)
