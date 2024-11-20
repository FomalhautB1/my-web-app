from flask import Flask, render_template, Response, jsonify
import requests
import cv2

app = Flask(__name__)

# IP реле (заменить на ваш)
RELAY_IP = "http://192.168.1.100/cm?user=admin&password=admin"

# Управление реле
@app.route('/relay/on', methods=['GET'])
def relay_on():
    response = requests.get(f"{RELAY_IP}&power=on")
    return jsonify({"status": "on" if response.status_code == 200 else "error"}), response.status_code

@app.route('/relay/off', methods=['GET'])
def relay_off():
    response = requests.get(f"{RELAY_IP}&power=off")
    return jsonify({"status": "off" if response.status_code == 200 else "error"}), response.status_code

# Видеострим
def generate_video_stream():
    # IP-камера или путь к USB-камере
    video_capture = cv2.VideoCapture(0)  # Если используете IP-камеру, замените на правильный URL
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        _, jpeg = cv2.imencode('.jpg', frame)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video')
def video():
    return Response(generate_video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
