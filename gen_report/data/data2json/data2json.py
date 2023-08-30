import json
import openpyxl

xlsx_file = "pair_2000.xlsx"

def pair2json():
    wb = openpyxl.load_workbook(xlsx_file)
    sheet = wb.active
    row_num = 0
    titles = []
    lst = []

    for row in sheet.rows:
        row_num += 1

        if row_num == 1:
            # 表头
            for cell in row:
                # 移除空格
                value = cell.value.replace(' ', '')
                titles.append(value)
        else:
            # 内容
            item = {}
            for key, cell in zip(titles, row):
                text = str(cell.value)
                text = text.replace(' ', '')
                text = text.replace('\n', '')
                item[key] = text

            lst.append(item)
    print("问答对数量："+str(len(lst)))

    return lst

if __name__ == '__main__':
    data = pair2json()
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    print(json_str)
    with open('../acco_ques_pair_2000.json','w') as f:
        f.write(json_str.encode("gbk", 'ignore').decode("gbk", "ignore"))