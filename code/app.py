from flask import Flask, render_template, Response, jsonify
import cv2

app = Flask(__name__)

stream_is_off = True
RELAY_IP = "http://192.168.1.100/cm?user=admin&password=admin"

@app.route('/relay/on', methods=['GET'])
def relay_on():
    response = requests.get(f"{RELAY_IP}&power=on")
    return jsonify({"status": "on" if response.status_code == 200 else "error"}), response.status_code

@app.route('/relay/off', methods=['GET'])
def relay_off():
    response = requests.get(f"{RELAY_IP}&power=off")
    return jsonify({"status": "off" if response.status_code == 200 else "error"}), response.status_code

@app.route('/stream/on_off', methods=['GET'])
def stream_switch():
    global stream_is_off
    stream_is_off = not stream_is_off
    return jsonify({"status": "off" if stream_is_off else "on"}), 200

def generate_video_stream():
    global stream_is_off
    video_capture = None

    try:
        # Инициализация камеры при запуске потока
        video_capture = cv2.VideoCapture(0)
        if not video_capture.isOpened():
            return  # Прерываем поток, если камера недоступна

        while not stream_is_off:
            ret, frame = video_capture.read()
            if not ret:
                break  # Останавливаем поток, если кадры не читаются
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
    finally:
        # Освобождаем ресурсы камеры
        if video_capture:
            video_capture.release()

@app.route('/video')
def video():
    if stream_is_off:
        return jsonify({"error": "Stream is off"}), 404
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)