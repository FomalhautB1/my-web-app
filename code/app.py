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

@app.route('/stream/status', methods=['GET'])
def stream_status():
    global stream_is_off
    return jsonify({"status": "off" if stream_is_off else "on"}), 200

@app.route('/stream/on', methods=['GET'])
def stream_on():
    global stream_is_off
    stream_is_off = False
    generate_video_stream()
    return jsonify({"status": "on"}), 200

@app.route('/stream/off', methods=['GET'])
def stream_off():
    global stream_is_off
    stream_is_off = True
    return jsonify({"status": "off"}), 200

def generate_video_stream():
    global stream_is_off
    try:
        while not stream_is_off:
            # Создаем новый объект камеры
            video_capture = cv2.VideoCapture(0)
            if not video_capture.isOpened():
                print("Error: Unable to open camera")
                stream_is_off = True
                break

            while not stream_is_off:
                ret, frame = video_capture.read()
                if not ret:
                    print("Error: Unable to read frame")
                    break

                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

            # Освобождаем ресурсы после использования
            video_capture.release()
            print("Camera released")
            break
    except Exception as e:
        print(f"Error in generate_video_stream: {e}")

@app.route('/video')
def video():
    if stream_is_off:
        return jsonify({"error": "Stream is off"}), 404
    try:
        print("Starting video stream")
        return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(f"Error in video endpoint: {e}")
        return jsonify({"error": "Failed to start video stream"}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)