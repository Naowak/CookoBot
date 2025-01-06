import requests
import json
from dotenv import load_dotenv
import os
import time

# Load the .env file
dotenv = load_dotenv()

def make_prompt(user_message, objects, player):
    # Create a prompt
    prompt = f"""The user will give you an instruction, you have to transform it into a command that the player can execute. 
    The player is on a 15x15 tile map with different objects on some tiles.

    The player can do 3 different actions:
    - MOVE X,Y : move the player to the tile at position X,Y
    - PICK : pick up the object on the tile where the player is
    - DROP : drop the first object the player is holding

    To help you provide the best command, you will get the following informations:
    - the player position (X,Y)
    - the position of the objects on the map
    - the user instruction

    You must follow the following rules:
    1. You must only provide a command that the player can execute : MOVE X,Y, PICK or DROP.
    2. You must reason on the user instruction and the player position to provide the best command.

    You should only respond in the format as described below:
    RESPONSE FORMAT:
    THOUGHTS: Based on the information you get, do reasoning about what the command should be.
    COMMAND: The best command you find.
    
    Here is an example of the interaction:

    EXAMPLE INFORMATIONS:
    PLAYER POSITION: {{'x': 10, 'y': 2}}
    OBJECTS POSITION: {{(0, 3): 'Pomme', (1, 8): 'Poire', (1, 12): 'Poire', (13, 10): 'Banane'}}
    USER_MESSAGE: Ramasse une poire

    EXAMPLE RESPONSE:
    THOUGHTS: The player is at position 10,2 and there is two poires on the map: in 1,12 and 13,10.
    The player can not pick up a poire in its current position because there is no poire on the tile.
    Based on the manhattan distance, the closest poire is in 13,10.
    The player should move to the closest poire in 13,10 now so it can pick it up on the next interaction.
    COMMAND: MOVE 13,10
    
    Now it's your turn:

    INFORMATIONS:
    PLAYER POSITION: {player}
    OBJECTS POSITION: {objects}
    USER_MESSAGE: {user_message}
    
    RESPONSE:
    """
    
    return prompt

# Function to extract the thoughts and command from the text
def extract_thoughts_and_command(text):
    # Initialiser les variables pour stocker les thoughts et la commande
    thoughts = None
    action = None
    coordinates = None

    # Extraire les thoughts
    if "THOUGHTS:" in text:
        start_thoughts = text.index("THOUGHTS:") + len("THOUGHTS:")
        end_thoughts = text.index("COMMAND:")
        thoughts = text[start_thoughts:end_thoughts].strip()

    # Extraire la commande
    if "COMMAND:" in text:
        command_part = text.split("COMMAND:")[1].strip()
        
        # Vérifier le type de commande et l'extraire
        if command_part.startswith("MOVE"):
            parts = command_part.split(" ")
            action = parts[0]
            coordinates = parts[1] if len(parts) > 1 else None
        elif command_part.startswith("PICK") or command_part.startswith("DROP"):
            action = command_part.split(" ")[0]
            coordinates = None

    return thoughts, action, coordinates

# Function to make a request to the API
def make_request(prompt):

    def send_request():
        # Make a request to the API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('API_KEY')}",
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat", # Optional
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        return response.json()
    
    # Send request 
    response = send_request()
    # print(response)

    # Check if the rate limit was reached
    while('error' in response and response['error']['code'] == 429): 
        # Wait for 30 seconds and try again
        print('Rate limit reached, waiting for 30 seconds')
        time.sleep(30)
        response = send_request()

    # Check if the request was successful
    if 'error' in response:
        raise Exception(f"Failed to make the request: {response.json()}")

    # Get the answer from the response
    answer = response['choices'][0]['message']['content']
    # print(answer)
    return answer