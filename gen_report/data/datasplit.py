import pandas as pd
from sklearn.model_selection import train_test_split
import json

# 读取xlsx文件
xlsx_path = './data2json/pair.xlsx'
data = pd.read_excel(xlsx_path)

# 假设数据集中有两列 'features' 和 'target'
X = data[['according']]
y = data['question']

# 划分数据集为训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 将划分后的数据保存为JSON文件
train_data = {
    "X": X_train.to_dict(orient='records'),
    "y": y_train.tolist()
}

test_data = {
    "X": X_test.to_dict(orient='records'),
    "y": y_test.tolist()
}

# 将数据保存为JSON文件
train_json_path = 'train_data.json'
test_json_path = 'test_data.json'

with open(train_json_path, 'w') as json_file:
    json.dump(train_data, json_file, indent=4)

with open(test_json_path, 'w') as json_file:
    json.dump(test_data, json_file, indent=4)