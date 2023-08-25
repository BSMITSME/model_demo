from kafka import KafkaConsumer, KafkaProducer
from PIL import Image
from io import BytesIO
import os
from EasyOCR.easyocr import easyocr
import json
import numpy as np
import papago as pg
import cv2
import base64
import traceback

reader = easyocr.Reader(lang_list = ['ko'], recog_network = 'trocr', gpu=True)

consumer = KafkaConsumer('topic',
                         bootstrap_servers = ['52.91.126.82:9092','34.232.53.143:9092','100.24.240.6:9092'],
                         auto_offset_reset = 'latest'
                         )

producer = KafkaProducer(acks='all',
                         compression_type='gzip',
                         bootstrap_servers=['52.91.126.82:9092','34.232.53.143:9092','100.24.240.6:9092'])

def on_send_success(record_metadata) : 
    print("메시지 전송 성공. Topic:", record_metadata.topic, "Partition:", record_metadata.partition, "Offset:", record_metadata.offset)

def on_send_error(e):
    print("메시지 전송 실패:", e)

def switch_json(message):
    ko_message = message[:]
    en_message = message[:]
    jp_message = message[:]
    
    for i, sentence in enumerate(message):
        data = json.loads(sentence)
        bounding_box_pos = data['boxes']
        text = data['text']
        confident = data['confident']
        background_color = data['background_color']
        text_color = data['text_color']
        
        print(f"type : {type(text)}, text : {text}")
        result_jp = pg.get_translate(text, 'ja')
        result_en = pg.get_translate(text, 'en')
        result_ko = pg.get_translate(text, 'ko')
        data['text'] = result_ko
        ko_message[i] = json.dumps(data)
        
        data['text'] = result_en
        en_message[i] = json.dumps(data)
        
        data['text'] = result_jp
        jp_message[i] = json.dumps(data)
    
    # for a, b, c in message :
    #     print(f"type : {type(b)}, text : {b}")
    #     # 한국어, 영어, 일본어 번역
    #     result_jp = pg.get_translate(b, 'ja')
    #     result_en = pg.get_translate(b, 'en')
    #     result_ko = pg.get_translate(b, 'ko')
    #     dic_jp[result_jp] = a
    #     dic_en[result_en] = a
    #     dic_ko[result_ko] = a


    json_data_ko = json.dumps(ko_message, cls=NpEncoder)
    json_data_en = json.dumps(en_message, cls=NpEncoder)
    json_data_jp = json.dumps(jp_message, cls=NpEncoder)
    print ('final Result')
    print (json_data_en, json_data_ko, json_data_jp)
    return json_data_ko, json_data_en, json_data_jp

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)
    
def processincomsumer(message):
    global reader
    message = base64.b64decode(message)
    img = BytesIO(message)
    img= np.array(Image.open(img))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    print (type(img))
    #print (type(img))
    #img.save(f"pro.jpg")
    
    # 바운딩 박스, 텍스트, 임계값
    #result = reader.readtext(f"pro.jpg")
    result = reader.readtext(img, batch_size = 10, output_format='json_specific_and_relative_pos')
    #os.remove(f"pro.jpg")
    
    print(result)

    re_ko, re_en, re_jp = switch_json(result)
    print(f"""re_ko : {re_ko}""")
    print(f"""re_en : {re_en}""")
    print(f"""re_jp : {re_jp}""")
    producer.send('korean', re_ko.encode('utf-8')).add_callback(on_send_success).add_errback(on_send_error)
    producer.send('english', re_en.encode('utf-8')).add_callback(on_send_success).add_errback(on_send_error)
    producer.send('japan', re_jp.encode('utf-8')).add_callback(on_send_success).add_errback(on_send_error)


if __name__ == '__main__' : 
    for message in consumer :
        
        try :
            processincomsumer(message.value)
        except Exception as e:
            print (f"Error : {e}")
            print (traceback.format_exc())

