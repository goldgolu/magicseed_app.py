from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
from pymongo import MongoClient
import random
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client['airdrop_game']
users_collection = db['users']
inventory_collection = db['inventory']

# Game Variables
environments = ['forest', 'mountain', 'swamp', 'desert', 'ruined_city', 'village', 'castle']
rooms = {}

def generate_airdrop():
    """Random airdrop generator"""
    items = ["Gold Coins", "Weapon Upgrade", "Health Potion", "Mystery Box"]
    return random.choice(items)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.json
    username = data.get("username")
    selected_environment = random.choice(environments)
    user = users_collection.find_one({"username": username})
    if not user:
        users_collection.insert_one({"username": username, "coins": 100, "level": 1})
    return jsonify({
        'environment': selected_environment,
        'airdrop': generate_airdrop(),
        'message': f'Welcome {username}, explore and survive!'
    })

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

if __name__ == '__main__':
    socketio.run(app, debug=True)
