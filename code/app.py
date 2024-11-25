from flask import Flask, render_template, redirect, url_for, jsonify, request, make_response, Response
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
)
import requests
import cv2
from flask_bcrypt import Bcrypt

# Создание приложения Flask
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_secret_key'
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False  # Установить True, если используется HTTPS
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Для простоты

# Инициализация менеджера JWT и шифрования паролей
jwt = JWTManager(app)
bcrypt = Bcrypt()

relays = {}
# Пользовательские данные
users = {
    'user': bcrypt.generate_password_hash('password123').decode('utf-8')
}

# Переменная состояния
stream_is_off = True
RELAY_IP = "http://192.168.1.100/cm?user=admin&password=admin"

# === Авторизация и маршруты === #

@app.before_request
def redirect_to_login():
    """Перенаправляет пользователя на страницу логина, если токен отсутствует."""
    if request.endpoint is None:  # Проверяем, что endpoint существует
        return  # Разрешаем обработку без перенаправления

    if request.endpoint not in ['login', 'static'] and not request.endpoint.startswith('static'):
        try:
            verify_jwt_in_request()
        except Exception as e:
            print(f"Redirecting to login: {e}")
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Обрабатывает запросы логина."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Проверяем пользователя
        if username in users and bcrypt.check_password_hash(users[username], password):
            access_token = create_access_token(identity=username)
            response = make_response(redirect(url_for('protected')))
            response.set_cookie(
                'access_token_cookie',  # Имя должно совпадать с ожидаемым
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
    """Обнуляет токен пользователя."""
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('access_token')
    return response



@app.route('/relay/add', methods=['POST'])
@jwt_required()
def add_relay():
    """Adds a new relay."""
    global relays
    relay_id = len(relays) + 1
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            return jsonify({"error": "Invalid JSON or empty request"}), 400

        ip = data.get('ip')
        name = data.get('name', f'Relay {relay_id}')

        if not ip:
            return jsonify({"error": "IP address is required"}), 400

        relays[relay_id] = {"ip": ip, "name": name}
        return jsonify({"message": "Relay added", "id": relay_id}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/protected')
@jwt_required()
def protected():
    """Маршрут для проверки токена."""
    current_user = get_jwt_identity()
    return render_template('index.html', username=current_user)

# === Реле и поток === #

@app.route('/relay/on', methods=['GET'])
@jwt_required()
def relay_on():
    """Включает реле."""
    try:
        response = requests.get(f"{RELAY_IP}&power=on")
        return jsonify({"status": "on" if response.status_code == 200 else "error"}), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/relay/off', methods=['GET'])
@jwt_required()
def relay_off():
    """Выключает реле."""
    try:
        response = requests.get(f"{RELAY_IP}&power=off")
        return jsonify({"status": "off" if response.status_code == 200 else "error"}), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stream/on', methods=['GET'])
@jwt_required()
def stream_on():
    """Включает поток."""
    global stream_is_off
    stream_is_off = False
    return jsonify({"status": "on"}), 200

@app.route('/stream/off', methods=['GET'])
@jwt_required()
def stream_off():
    """Выключает поток."""
    global stream_is_off
    stream_is_off = True
    return jsonify({"status": "off"}), 200

@app.route('/stream/status', methods=['GET'])
@jwt_required()
def stream_status():
    """Возвращает статус потока."""
    global stream_is_off
    return jsonify({"status": "off" if stream_is_off else "on"}), 200

@app.route('/video')
@jwt_required()
def video():
    """Возвращает видеопоток."""
    if stream_is_off:
        return jsonify({"error": "Stream is off"}), 404
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_video_stream():
    """Генератор видеопотока."""
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
    """Перенаправляет на защищенный маршрут."""
    return redirect(url_for('protected'))

# Запуск приложения
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)