from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import google.generativeai as genai
import uuid
from models import PromptEngineer
from utils import cache_response, get_cached_response, version_file, render_preview, User

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Change in production
socketio = SocketIO(app, cors_allowed_origins="*")

login_manager = LoginManager()
login_manager.init_app(app)

# Configure Gemini AI
genai.configure(api_key='your-gemini-api-key')
model = genai.GenerativeModel('gemini-1.5-flash')  # Updated to latest model
prompt_engineer = PromptEngineer()

# In-memory storage for simplicity (use DB in production)
users = {}
rooms = {}  # Room: {user_id: code}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = str(uuid.uuid4())
        users[user_id] = User(user_id)
        login_user(users[user_id])
        cache_response(f'auth:{user_id}', 'authenticated', 3600)  # Cache auth
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/generate', methods=['POST'])
@login_required
def generate_code():
    prompt = request.form['prompt']
    room = request.form.get('room', 'default')
    context = rooms.get(room, {}).get(current_user.id, [])
    
    # Refine prompt with ML
    refined_prompt = prompt_engineer.refine_prompt(prompt, context)
    
    # Check cache
    cached = get_cached_response(f'code:{refined_prompt}')
    if cached:
        code = cached.decode()
    else:
        # Generate with Gemini
        try:
            response = model.generate_content(refined_prompt)
            code = response.text
            cache_response(f'code:{refined_prompt}', code)
        except Exception as e:
            code = f"Error generating code: {str(e)}"
    
    # Update context
    context.append(prompt)
    rooms.setdefault(room, {})[current_user.id] = context[-10:]  # Keep last 10
    
    # Version and preview
    filepath = f'static/{room}_{current_user.id}.py'
    try:
        with open(filepath, 'w') as f:
            f.write(code)
        version_file(filepath, f"Generated code for {prompt}")
    except Exception as e:
        print(f"Versioning error: {e}")  # Log error without crashing
    preview = render_preview(code)
    
    socketio.emit('code_update', {'code': code, 'preview': preview}, room=room)
    return jsonify({'code': code, 'preview': preview})

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('status', {'msg': f'{current_user.id} joined {room}'}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('status', {'msg': f'{current_user.id} left {room}'}, room=room)

@socketio.on('edit_code')
def on_edit_code(data):
    room = data['room']
    code = data['code']
    rooms.setdefault(room, {})[current_user.id] = code
    emit('code_update', {'code': code}, room=room, skip_sid=request.sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)