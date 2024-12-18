from flask import Flask, render_template, redirect, url_for, jsonify, request, make_response, Response
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
)
import requests
import cv2
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_secret_key'
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False  
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  

jwt = JWTManager(app)
bcrypt = Bcrypt()

relays = {}
users = {
    'user': bcrypt.generate_password_hash('password123').decode('utf-8')
}

ip = ''
name = ''

stream_is_off = True
RELAY_IP = ip


@app.before_request
def redirect_to_login():

    if request.endpoint is None:  
        return  

    if request.endpoint not in ['login', 'static'] and not request.endpoint.startswith('static'):
        try:
            verify_jwt_in_request()
        except Exception as e:
            print(f"Redirecting to login: {e}")
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in users and bcrypt.check_password_hash(users[username], password):
            access_token = create_access_token(identity=username)
            response = make_response(redirect(url_for('protected')))
            response.set_cookie(
                'access_token_cookie',  
                access_token,
                httponly=True,
                secure=False,
                samesite='Strict'
            )
            print(f"Redirecting to /protected with token: {access_token}")
            return response

        else:
            return render_template('login.html', error="Неверные учетные данные")

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('access_token')
    return response



@app.route('/relay/add', methods=['POST'])
@jwt_required()
def add_relay():
    global relays, RELAY_IP
    relay_id = len(relays) + 1
    try:
        data = request.get_json()  
        if not data:
            return jsonify({"error": "Invalid JSON or empty request"}), 400

        RELAY_IP = data.get('ip')  
        name = data.get('name', f'Relay {relay_id}')

        if not RELAY_IP:
            return jsonify({"error": "IP address is required"}), 400

        relays[relay_id] = {"ip": RELAY_IP, "name": name}
        return jsonify({"message": "Relay added", "id": relay_id}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/protected')
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return render_template('index.html', username=current_user)

@app.route('/relay/on', methods=['GET'])
@jwt_required()
def relay_on():
    try:
        response = requests.get(f"http://{RELAY_IP}/cm?cmnd=Power1 ON", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "on"}), 200
        return jsonify({"error": f"Unexpected response from relay: {response.status_code}"}), response.status_code
    except requests.Timeout:
        return jsonify({"error": "Timeout occurred while connecting to relay"}), 504
    except requests.RequestException as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500




@app.route('/relay/off', methods=['GET'])
@jwt_required()
def relay_off():
    try:
        response = requests.get(f"http://{RELAY_IP}/cm?cmnd=Power1 OFF", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "off"}), 200
        return jsonify({"error": f"Unexpected response from relay: {response.status_code}"}), response.status_code
    except requests.Timeout:
        return jsonify({"error": "Timeout occurred while connecting to relay"}), 504
    except requests.RequestException as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500




@app.route('/stream/on', methods=['GET'])
@jwt_required()
def stream_on():
    global stream_is_off
    stream_is_off = False
    return jsonify({"status": "on"}), 200

@app.route('/stream/off', methods=['GET'])
@jwt_required()
def stream_off():
    global stream_is_off
    stream_is_off = True
    return jsonify({"status": "off"}), 200

@app.route('/stream/status', methods=['GET'])
@jwt_required()
def stream_status():
    global stream_is_off
    return jsonify({"status": "off" if stream_is_off else "on"}), 200

@app.route('/video')
@jwt_required()
def video():
    if stream_is_off:
        return jsonify({"error": "Stream is off"}), 404
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_video_stream():
    global stream_is_off
    video_capture = cv2.VideoCapture(0)
    try:
        while not stream_is_off:
            ret, frame = video_capture.read()
            if not ret:
                break
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
    finally:
        video_capture.release()

@app.route('/')
def index():
    return redirect(url_for('protected'))

# Запуск приложения
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)