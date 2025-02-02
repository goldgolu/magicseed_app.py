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

# AI Bot class for handling tasks and user issues
class AIBot:
    def __init__(self, owner_id):
        self.owner_id = owner_id

    def handle_task(self, task, user_id, permission_required=False):
        """
        Bot will handle tasks and request permission for critical actions
        """
        if permission_required and user_id != self.owner_id:
            return f"Permission required from the owner to complete the task."
        if task == "manage_airdrop":
            # Example task for managing airdrop
            return self.manage_airdrop(user_id)
        elif task == "fix_bug":
            # Example task for fixing a bug
            return self.fix_bug(user_id)
        else:
            return f"Task '{task}' is not recognized."
    
    def manage_airdrop(self, user_id):
        # Logic to manage airdrop
        return f"Airdrop for {user_id} has been managed successfully."
    
    def fix_bug(self, user_id):
        # Example logic for bug fixing
        return f"Bug fixed for {user_id}. Please try again."

# Initialize the AI bot
ai_bot = AIBot(owner_id="admin_user")  # Replace with actual owner ID

def generate_airdrop():
    """Random airdrop generator"""
    items = ["Gold Coins", "Weapon Upgrade", "Health Potion", "Mystery Box"]
    return random.choice(items)

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

# API endpoint for AI Bot to manage tasks
@app.route('/ai_bot/manage_task', methods=['POST'])
def manage_task():
    data = request.json
    task = data.get("task")
    user_id = data.get("user_id")
    permission_required = data.get("permission_required", False)
    
    task_response = ai_bot.handle_task(task, user_id, permission_required)
    return jsonify({"response": task_response})

# API to manage bot permissions (only owner can set)
@app.route('/ai_bot/set_permission', methods=['POST'])
def set_permission():
    data = request.json
    user_id = data.get("user_id")
    permission = data.get("permission")
    
    if user_id == ai_bot.owner_id:
        ai_bot.owner_id = user_id  # Owner can change permissions
        return jsonify({"response": f"Permission updated to {user_id}"})
    else:
        return jsonify({"response": "Permission denied. Only the owner can make this change."})

if __name__ == '__main__':
    socketio.run(app, debug=True)
