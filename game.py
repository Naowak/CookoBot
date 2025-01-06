import arcade
import random
import time
from queue import PriorityQueue
import arcade.gui
from collections import deque
from constants import *
from llm_request import make_request, make_prompt, extract_thoughts_and_command

class CookoBot(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "CookoBot")
        """Initialisation de la fenêtre de jeu."""
        self.player = None
        self.inventory = []
        self.objects = ['Banane', 'Pomme', 'Poire']
        self.items_on_map = {}
        self.path = []  # Chemin calculé
        self.path_index = 0  # Indice du prochain pas à suivre
        self.step_count = 0  # Compteur de pas
        self.action_count = 0  # Compteur d'actions
        self.inventory = deque(maxlen=INVENTORY_SIZE)  # Inventaire limité à 3 objets
        self.llm_activated = True

        # Create a horizontale BoxGroup to align buttons
        self.action_box = arcade.gui.UIBoxLayout(vertical=False, x=MENU_X, y=INVENTORY_BUTTON_Y)
        self.chat_box = arcade.gui.UIBoxLayout(vertical=True, x=INSTRUCTION_TEXT_X, y=INSTRUCTION_TEXT_Y)

        # Créer le bouton de ramassage
        pick_up_button = arcade.gui.UIFlatButton(text="Ramasser", width=BUTTON_WIDTH, style=BUTTON_MAUVE)
        pick_up_button.on_click = self.action_pick
        self.action_box.add(pick_up_button.with_space_around(right=PADDING))

        # Créer le bouton de dépôt
        drop_button = arcade.gui.UIFlatButton(text="Déposer", width=BUTTON_WIDTH, style=BUTTON_MAUVE)
        drop_button.on_click = self.action_drop
        self.action_box.add(drop_button)

        # Créer la zone de texte
        self.text_input = arcade.gui.UIInputText(height=INSTRUCTION_TEXT_HEIGHT, width=INSTRUCTION_TEXT_WIDTH,
            text_color=arcade.color.MAUVE_TAUPE, font_size=14, text="Attrape une pomme !", multiline=True)
        self.chat_box.add(self.text_input)

        # Créer le bouton d'envoi
        send_button = arcade.gui.UIFlatButton(text="Envoyer", width=BUTTON_WIDTH, style=BUTTON_MAUVE)
        send_button.on_click = self.send_instruction
        self.chat_box.add(send_button.with_space_around(top=PADDING+INSTRUCTION_BOX_PADDING))

        # Créer un checkbox pour activer le LLM
        self.llm_checkbox = arcade.gui.UIFlatButton(text="Désactiver le LLM", width=2*BUTTON_WIDTH, height=35, 
                                                    style=BUTTON_TUSCANY)
        self.llm_checkbox.on_click = self.on_activation_llm_press
        self.chat_box.add(self.llm_checkbox.with_space_around(top=PADDING))
        
        # Créer le gestionnaire d'interface utilisateur
        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.manager.add(self.action_box)
        self.manager.add(self.chat_box)


    def setup(self):
        """Initialisation de la carte et du personnage."""
        # Background
        arcade.set_background_color(BACKGROUND_COLOR)

        # Création de la carte & positionnement du personnage
        x_start = random.randint(0, NB_TILES - 1)
        y_start = random.randint(0, NB_TILES - 1)
        self.player = {'x': x_start, 'y': y_start}  # Position initiale du personnage

        # Chargement des textures
        self.player_texture = arcade.load_texture("images/robot.png")
        self.fruit_textures = {
            'Banane': arcade.load_texture("images/banane.png"),
            'Pomme': arcade.load_texture("images/pomme.png"),
            'Poire': arcade.load_texture("images/poire.png")
        }

        # Placement aléatoire des objets sur la carte
        for _ in range(NB_OBJ):  # NB_OBJ objects aléatoires
            x = random.randint(0, NB_TILES - 1)
            y = random.randint(0, NB_TILES - 1)
            fruit = random.choice(self.objects)
            self.items_on_map[(x, y)] = fruit
        

    def on_draw(self):
        """Rendu de l'écran."""
        arcade.start_render()

        # Dessiner le chemin restant en orange
        if self.path and self.path_index < len(self.path):
            for step in self.path[self.path_index:]:
                position_x = step[0] * TILE_SIZE + TILE_SIZE // 2 + PADDING
                position_y = step[1] * TILE_SIZE + TILE_SIZE // 2 + PADDING
                arcade.draw_rectangle_filled(position_x, position_y, TILE_SIZE, TILE_SIZE, (220, 205, 205))

        # Dessiner la grille
        arcade.draw_rectangle_outline(PADDING + MAP_SIZE//2, PADDING + MAP_SIZE//2, MAP_SIZE, MAP_SIZE, arcade.color.MAUVE_TAUPE, border_width=4)
        for row in range(NB_TILES):
            for col in range(NB_TILES):
                x = col * TILE_SIZE + PADDING
                y = row * TILE_SIZE + PADDING
                arcade.draw_rectangle_outline(x + TILE_SIZE // 2, y + TILE_SIZE // 2, TILE_SIZE, TILE_SIZE, arcade.color.MAUVE_TAUPE)
        
        # Dessiner les objets sur la carte
        for (x, y), fruit in self.items_on_map.items():
            position_x = x * TILE_SIZE + TILE_SIZE // 2 + PADDING
            position_y = y * TILE_SIZE + TILE_SIZE // 2 + PADDING
            arcade.draw_texture_rectangle(position_x, position_y, OBJ_SIZE, OBJ_SIZE, self.fruit_textures[fruit])

        # Dessiner le personnage
        arcade.draw_texture_rectangle(
            self.player['x'] * TILE_SIZE + TILE_SIZE // 2 + PADDING,
            self.player['y'] * TILE_SIZE + TILE_SIZE // 2 + PADDING,
            OBJ_SIZE, OBJ_SIZE, self.player_texture
        )

        # Afficher le compteur de pas
        arcade.draw_texture_rectangle(POINT_BOX_X, POINT_BOX_Y, LOGO_SIZE, LOGO_SIZE, arcade.load_texture("images/walk.png"))
        arcade.draw_text(f"{self.step_count}", POINT_BOX_X+LOGO_SIZE-10, POINT_BOX_Y-LOGO_SIZE//2+10, arcade.color.MAUVE_TAUPE, 16, font_name="Comic Sans MS")

        # Afficher le compteur d'actions
        arcade.draw_texture_rectangle(POINT_BOX_X+MENU_WIDTH//2, POINT_BOX_Y, LOGO_SIZE, LOGO_SIZE, arcade.load_texture("images/star.png"))
        arcade.draw_text(f"{self.action_count}", POINT_BOX_X+MENU_WIDTH//2+LOGO_SIZE-10, POINT_BOX_Y-LOGO_SIZE//2+10, arcade.color.MAUVE_TAUPE, 16, font_name="Comic Sans MS")

        # Afficher l'inventaire au-dessus des boutons
        arcade.draw_text(f"Inventaire ({len(self.inventory)}/{INVENTORY_SIZE})", MENU_X, INVENTORY_TITLE_Y, arcade.color.MAUVE_TAUPE, 16, font_name="Comic Sans MS")
        arcade.draw_rectangle_outline(MENU_X + MENU_WIDTH//2, INVENTORY_BOX_Y - INVENTORY_BOX_HEIGHT//2, MENU_WIDTH, INVENTORY_BOX_HEIGHT, arcade.color.MAUVE_TAUPE)
        for i, item in enumerate(self.inventory):
            arcade.draw_text(item, INVENTORY_TEXT_X, INVENTORY_TEXT_Y - INVENTORY_TEXT_HEIGHT*i, arcade.color.MAUVE_TAUPE, 16, font_name="Comic Sans MS")

        # Afficher le chat
        arcade.draw_text("Instruction", MENU_X, INSTRUCTION_TITLE_Y, arcade.color.MAUVE_TAUPE, 16, font_name="Comic Sans MS")
        arcade.draw_rectangle_outline(MENU_X + MENU_WIDTH//2, INSTRUCTION_BOX_Y-INSTRUCTION_BOX_HEIGHT//2, MENU_WIDTH, INSTRUCTION_BOX_HEIGHT, arcade.color.MAUVE_TAUPE)

        # Afficher les boutons
        self.manager.draw()


    def on_mouse_press(self, x, y, button, modifiers):
        """Gestion des clics de souris.
        
        Args:
            x (int): Coordonnée x du clic de souris.
            y (int): Coordonnée y du clic de souris.
            button (int): Bouton de la souris cliqué.
            modifiers (int): Modificateurs de la touche de la souris.
        """
        # Convertir les coordonnées de la souris en coordonnées de la grille
        grid_x = (x - PADDING) // TILE_SIZE
        grid_y = (y - PADDING) // TILE_SIZE

        # Vérifier si la case est valide
        if 0 <= grid_x < NB_TILES and 0 <= grid_y < NB_TILES:
            # Calculer le chemin vers la case
            self.path = self.a_star(self.player['x'], self.player['y'], grid_x, grid_y)
            if self.path:
                self.path_index = 0  # Réinitialise l'index de l'étape
                self.action_move()
    

    def on_activation_llm_press(self, event=None):
        """Active ou désactive le LLM.
        
        Args:
            event (arcade.gui.UIEvent): Événement de l'interface utilisateur.
        """
        self.llm_activated = not self.llm_activated
        self.llm_checkbox.text = "Désactiver le LLM" if self.llm_activated else "Activer le LLM"
        print("LLM activé" if self.llm_activated else "LLM désactivé")


    def a_star(self, start_x, start_y, goal_x, goal_y):
        """Implémentation de l'algorithme A*.
        
        Args:
            start_x (int): Coordonnée x de départ.
            start_y (int): Coordonnée y de départ.
            goal_x (int): Coordonnée x de destination.
            goal_y (int): Coordonnée y de destination.
        """
        def heuristic(x1, y1, x2, y2):
            return abs(x1 - x2) + abs(y1 - y2)

        # Initialisation des structures de données
        open_set = PriorityQueue()
        open_set.put((0, (start_x, start_y)))
        came_from = {}
        g_score = {pos: float('inf') for pos in [(x, y) for x in range(NB_TILES) for y in range(NB_TILES)]}
        g_score[(start_x, start_y)] = 0
        f_score = g_score.copy()
        f_score[(start_x, start_y)] = heuristic(start_x, start_y, goal_x, goal_y)

        # Recherche du chemin
        while not open_set.empty():
            # Extraire le nœud avec le score f le plus bas
            _, current = open_set.get()

            # Vérifier si on a atteint la destination
            if current == (goal_x, goal_y):
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            # Parcourir les voisins
            x, y = current
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # Déplacement N/S/E/O
                neighbor = (x + dx, y + dy)
                if 0 <= neighbor[0] < NB_TILES and 0 <= neighbor[1] < NB_TILES:  # Vérifier les limites
                    tentative_g_score = g_score[(x, y)] + 1
                    if tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = (x, y)
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + heuristic(neighbor[0], neighbor[1], goal_x, goal_y)
                        open_set.put((f_score[neighbor], neighbor))

        return None  # Aucun chemin trouvé


    def move_along_path(self, delta_time):
        """Déplace le personnage d'une case le long du chemin calculé."""
        # Vérifie si le chemin n'est pas terminé
        if self.path_index < len(self.path):
            # Déplace le personnage à l'étape suivante
            self.player['x'], self.player['y'] = self.path[self.path_index]
            self.path_index += 1
            self.step_count += 1 # Incrémente le compteur de pas
            self.on_draw()  # Redessine l'écran pour montrer le mouvement
        else:
            arcade.unschedule(self.move_along_path)  # Arrête la planification lorsque le déplacement est terminé
    

    def action_move(self, event=None):
        """Lance le déplacement du personnage vers une destination spécifiée.
        
        Args:
            event (arcade.gui.UIEvent): Événement de l'interface utilisateur.
        """
        # Execute le mouvement
        self.action_count += 1  # Incrémente le compteur d'actions
        arcade.unschedule(self.move_along_path)  # Arrête le déplacement actuel
        arcade.schedule(self.move_along_path, MOVE_DELAY)  # Planifie la fonction de déplacement


    def action_pick(self, event=None):
        """Ramasse un objet sur la carte. Si l'inventaire est plein, dépose l'objet le plus ancien.
        
        Args:
            event (arcade.gui.UIEvent): Événement de l'interface utilisateur.
        """
        # Vérifie si le joueur est sur une case avec un objet
        current_pos = (self.player['x'], self.player['y'])
        if current_pos in self.items_on_map:
            item = self.items_on_map[current_pos]
            if len(self.inventory) == INVENTORY_SIZE:  # Si l'inventaire est plein
                dropped_item = self.inventory.popleft()  # Retirer l'objet le plus ancien
                self.items_on_map[current_pos] = dropped_item  # Le déposer sur la cellule
            else:
                del self.items_on_map[current_pos]  # Retirer l'objet de la carte
            self.inventory.append(item)  # Ajouter l'objet à l'inventaire
            self.action_count += 1  # Incrémente le compteur d'actions


    def action_drop(self, event=None):
        """Dépose un objet sur la carte. Si un objet est déjà présent, échange les objets.
        Par défaut, dépose l'objet le plus ancien de l'inventaire.
        
        Args:
            event (arcade.gui.UIEvent): Événement de l'interface utilisateur.
        """
        # Vérifie si l'inventaire n'est pas vide
        if not self.inventory:
            return None
        
        # Execute l'action
        current_pos = (self.player['x'], self.player['y'])
        self.action_count += 1  # Incrémente le compteur d'actions
        if current_pos not in self.items_on_map:
            # Déposer l'objet sur la carte
            item_to_drop = self.inventory.popleft()  # Retirer le dernier objet de l'inventaire
            self.items_on_map[current_pos] = item_to_drop  # Le déposer sur la carte
        elif current_pos in self.items_on_map:
            # Échange avec l'objet existant
            existing_item = self.items_on_map[current_pos] # Récupérer l'objet existant
            item_to_drop = self.inventory.popleft() # Retirer le dernier objet de l'inventaire
            self.items_on_map[current_pos] = item_to_drop # Le déposer sur la carte
            self.inventory.append(existing_item) # Ajouter l'objet existant à l'inventaire
    

    def send_instruction(self, event=None):
        """Envoie l'instruction de l'utilisateur pour exécution. Si le LLM est activé, utilise la réponse du LLM.
        Sinon, exécute l'action spécifiée par l'utilisateur.
        
        Args:
            event (arcade.gui.UIEvent): Événement de l'interface utilisateur.
        """
        print("Instruction de l'utilisateur:", self.text_input.text)
        
        if self.llm_activated:
            # Demande au LLM de produire la commande
            prompt = make_prompt(self.text_input.text, self.items_on_map, self.player)
            answer = make_request(prompt)
            thoughts, action, coordinates = extract_thoughts_and_command(answer)
            
            # Affiche les informations extraites
            print("THOUGHTS:", thoughts)
            print("ACTION:", action)
            print("COORDINATES:", coordinates)
            if thoughts is None or action is None:
                print("Erreur lors de l'extraction des informations")
                return None
            
            # Update la valeur de l'entrée utilisateur par la commande extraite de la réponse du LLM
            self.text_input.text = (action + " " + coordinates) if coordinates else action
        
        # Actions possibles
        actions = {
            'PICK': self.action_pick,
            'DROP': self.action_drop,
            'MOVE': self.action_move,
        }

        # Extrait l'action de l'entrée utilisateur
        text_split = self.text_input.text.split(" ")
        if len(text_split) == 2:
            action, coordinates = text_split
        else:
            action, coordinates = text_split[0], None

        # Exécute l'action correspondante
        if action in actions:
            if action == 'MOVE' and coordinates:
                # Calculer le chemin vers les coordonnées spécifiées
                x, y = coordinates.split(",")
                self.path = self.a_star(self.player['x'], self.player['y'], int(x), int(y))
                if self.path:
                    self.path_index = 0
                else:
                    print("Chemin non trouvé")
                    return None

            # Exécute l'action
            actions[action]()

        # Efface le texte de l'entrée utilisateur
        self.text_input.clear()
        self.text_input.trigger_render()


if __name__ == "__main__":
    window = CookoBot()
    window.setup()
    arcade.run()
