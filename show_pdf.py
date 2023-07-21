# -*- coding: utf-8 -*-
# Date       ：2023/7/11
# Author     ：Chen Xuekai
# Description：渲染并写入html文件
import shutil
import random
from flask import Flask, render_template, request, jsonify
app = Flask(__name__, template_folder='templates')

tmp_html_file = "htmls_for_pdf.html"  # 网页上显示上传的PDF文件
html_code = r"""
<!DOCTYPE html>
<html>
<body>
    <embed height="1000" class="pdf" src="{{ url_for('static', filename="%s") }}" type="application/pdf" width="100%%">
</body>
</html>
"""


@app.route('/', methods=['GET', 'POST'])
# 开启服务，以便公网直接访问
@app.route('/get_pdf', methods=['GET', 'POST'])
def show_html():
    return render_template(tmp_html_file)


# 先根据pdf路径写html文件
@app.route('/render_html', methods=['POST'])
def convert_pdf_to_html():
    # 获取传入的 PDF 文件名
    pdf_fullname = request.get_json()['pdf_filename']
    # PDF复制到static中
    shutil.copy(pdf_fullname, "static")
    pdf_name = pdf_fullname.split("/")[-1]
    html_content = html_code % pdf_name

    # 将 HTML 内容保存到文件
    with open("./templates/htmls_for_pdf.html", 'w') as f:
        f.write(html_content)
    # 渲染模板，传入图像列表（加随机数的目的是提示gr.html刷新页面
    displaypdf_html = f"""<iframe height="1000" width="100%" src='http://10.112.9.164:8081/get_pdf' scrolling="no" frameborder="No">
        </iframe>编号：{random.randint(1, 1000000000)}
        """
    return jsonify({"out_html": displaypdf_html})


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8081)
