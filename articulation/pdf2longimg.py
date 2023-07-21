# -*- coding: utf-8 -*-
# Date       ：2023/7/7
# Author     ：Chen Xuekai
# # Description：
import os
from PIL import Image
import pdf2image


def pdf2longimage(pdf_path, start_page, end_page):
    output_folder = "/data/chenxuekai/ChatFin/tmp"
    output_img_path = os.path.join(output_folder, "new_output.jpg")
    # 将PDF转换为图像
    images = pdf2image.convert_from_path(pdf_path)
    # 保存图像文件
    for i, image in enumerate(images[start_page:end_page+1]):
        image.save(os.path.join("/data/chenxuekai/ChatFin/tmp", "output_"+str(i)+".jpg"))

    image_files = [os.path.join(output_folder, file) for file in os.listdir(output_folder)]

    # 打开图像文件
    images = [Image.open(file) for file in image_files]

    # 获取每个图像的宽度和高度
    widths, heights = zip(*(i.size for i in images))

    # 计算拼接后图像的总宽度和高度
    total_width = max(widths)
    max_height = sum(heights)

    # 创建一个空白图像作为目标图像
    result_image = Image.new("RGB", (total_width, max_height))

    # 拼接图像
    y_offset = 0
    for image in images:
        result_image.paste(image, (0, y_offset))
        y_offset += image.height

    # 显示拼接后的图像
    result_image.save(output_img_path)
    return output_img_path


# # 指定PDF文件路径
# pdf_path = "/data/chenxuekai/ChatFin/inputs/景杰生物招股说明书_30-33.pdf"
# print("图片已保存到：", pdf2longimage(pdf_path))