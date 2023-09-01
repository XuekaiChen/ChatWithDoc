# -*- coding: utf-8 -*-
# Date       ：2023/8/30
# Author     ：Chen Xuekai
# Description：
import fasttext
import jieba


def train_classifier(input_file_path, model_save_path):
    """训练分类模型"""

    # 基于 fasttext api 实现模型训练
    # https://fasttext.cc/docs/en/supervised-tutorial.html
    model = fasttext.train_supervised(input=input_file_path, label='__label__')
    result = model.test(input_file_path)
    print(result[1])
    print(result[2])
    model.save_model(model_save_path)


class Classifier:
    """分类器"""

    def __init__(self, model_load_path):
        self.model_load_path = model_load_path
        self.model = self.load_model()

    def load_model(self):
        """加载模型"""
        return fasttext.load_model(self.model_load_path)

    def predict(self, query):
        """预测 query"""

        # 基于 fasttext api 实现模型预测
        # https://fasttext.cc/docs/en/supervised-tutorial.html
        query_intent = self.model.predict(query)
        # 预测 label 和概率
        return query_intent[0][0].replace('__label__', ''), query_intent[1][0]


if __name__ == '__main__':
    classifier_corpus_path = "intention_classifier.train"
    classifier_save_path = "intention_classifier.bin"

    # train
    # print('开始训练分类器...')
    # train_classifier(classifier_corpus_path, classifier_save_path)
    # print('分类器训练成功...')

    # test
    classifier = Classifier(classifier_save_path)
    while True:
        question = input()
        words = " ".join(jieba.cut(question))
        print("分词后：", words)
        if question == 'q':
            break
        r1, r2 = classifier.predict(words)
        print(r1)
        print(r2)




