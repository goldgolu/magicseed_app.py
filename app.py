from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from pymongo import MongoClient
import random
import json
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = "your_secret_key_here"
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client['airdrop_game']
users_collection = db['users']
inventory_collection = db['inventory']
leaderboard_collection = db['leaderboard']

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Game Variables
environments = ['forest', 'mountain', 'swamp', 'desert', 'ruined_city', 'village', 'castle']
rooms = {}

# Scheduler for timed airdrops
scheduler = BackgroundScheduler()

def generate_airdrop():
    """Random airdrop generator"""
    items = ["Gold Coins", "Weapon Upgrade", "Health Potion", "Mystery Box"]
    return random.choice(items)

def timed_airdrop():
    """Scheduled function to generate timed airdrop"""
    print("Timed airdrop triggered!")

scheduler.add_job(timed_airdrop, 'interval', minutes=30)
scheduler.start()

@app.route('/')
def home():
    return render_template('index.html')  # Frontend UI

@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.json
    username = data.get("username")
    
    selected_environment = random.choice(environments)
    
    user = users_collection.find_one({"username": username})
    if not user:
        users_collection.insert_one({"username": username, "coins": 100, "level": 1, "last_login": "2025-02-02"})
    
    return jsonify({
        'environment': selected_environment,
        'airdrop': generate_airdrop(),
        'message': f'Welcome {username}, explore and survive!'
    })

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    user = User(username)  # Retrieve user from database
    login_user(user)
    return jsonify({"message": "Logged in!"})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out!"})

@app.route('/get_inventory', methods=['GET'])
def get_inventory():
    username = request.args.get("username")
    user_inventory = inventory_collection.find_one({"username": username})
    if not user_inventory:
        return jsonify({"message": "No inventory found."})
    return jsonify(user_inventory)

@app.route('/get_lobby_players', methods=['GET'])
def get_lobby_players():
    return jsonify({"players": list(rooms.keys())})

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    leaderboard = leaderboard_collection.find().sort("score", -1).limit(10)
    leaderboard_data = [{"username": player['username'], "score": player['score']} for player in leaderboard]
    return jsonify(leaderboard_data)

@socketio.on('join_lobby')
def join_lobby(data):
    username = data['username']
    room = "lobby"
    join_room(room)
    rooms[username] = room
    send(f"{username} joined the lobby", room=room)

@socketio.on('matchmaking')
def matchmaking(data):
    username = data['username']
    room_code = f"game_{random.randint(1000, 9999)}"
    join_room(room_code)
    rooms[username] = room_code
    send(f"{username} joined match {room_code}", room=room_code)

@socketio.on('claim_airdrop')
def claim_airdrop(data):
    username = data['username']
    item = generate_airdrop()
    inventory_collection.update_one({"username": username}, {"$push": {"items": item}}, upsert=True)
    send(f"{username} claimed {item}!", broadcast=True)

@socketio.on('earn_crypto')
def earn_crypto(data):
    username = data['username']
    amount = data['amount']
    users_collection.update_one({"username": username}, {"$inc": {"coins": amount}})
    send(f"{username} earned {amount} coins!", broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
