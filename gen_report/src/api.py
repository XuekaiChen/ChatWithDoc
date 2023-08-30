from gevent import pywsgi
from flask import Flask
from flask_restful import Resource, Api, reqparse
from transformers import AutoTokenizer, AutoModel
from flask_cors import CORS
import os
 
os.environ['CUDA_VISIBLE_DEVICES'] = '1'
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
api = Api(app)
 
tokenizer = AutoTokenizer.from_pretrained("/data/zhangyuhao/Information Disclosure/ChatGLM-Efficient-Tuning-main/export_model", trust_remote_code=True)
model = AutoModel.from_pretrained("/data/zhangyuhao/Information Disclosure/ChatGLM-Efficient-Tuning-main/export_model", trust_remote_code=True).half().cuda()
 
parser = reqparse.RequestParser()
parser.add_argument('according', type=str, help='Inputs for chat')
parser.add_argument('history', type=str, action='append', help='Chat history')
 
class Chat(Resource):
    def post(self):
        args = parser.parse_args()
        according = args['according']
        history = args['history'] or []
 
        response, new_history = model.chat(tokenizer, according, history)
        return {'question': response, 'new_history': new_history}
 
api.add_resource(Chat, '/api/chat')
if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 8001), app)
    server.serve_forever()
