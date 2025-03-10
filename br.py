import pygame, sys, json, random
with open("settings.json") as f: settings = json.load(f)
pygame.init()
screen = pygame.display.set_mode((settings["screen_width"], settings["screen_height"]))
clock = pygame.time.Clock()

# Helper to draw text using settings properties.
def draw_text(key, text, color=(255,255,255)):
    props = settings["text"][key]
    font_obj = pygame.font.SysFont(None, props["scale"])
    surf = font_obj.render(text, True, color)
    pos = props["pos"]
    if props.get("center"):
        pos = (pos[0] - surf.get_width()//2, pos[1] - surf.get_height()//2)
    screen.blit(surf, pos)

# Load sprite helper: scales to default_size if provided.
def load_sprite(key, default_size=None):
    path = settings.get(key, "")
    if path:
        try:
            img = pygame.image.load(path)
            if default_size: img = pygame.transform.scale(img, default_size)
            return img
        except:
            return None
    return None

# Load sprites
player_sprite = load_sprite("player_sprite", tuple(settings["player_size"]))
obstacle_sprite = load_sprite("obstacle_sprite")
healthy_sprite = load_sprite("healthy_sprite")
unhealthy_sprite = load_sprite("unhealthy_sprite")
background_sprite = load_sprite("background_sprite", (settings["screen_width"], settings["screen_height"]))

# Draw the background: sprite if available, else solid color.
def draw_background():
    if background_sprite:
        screen.blit(background_sprite, (0,0))
    else:
        screen.fill(settings["bg_color"])

# Track control flash usage.
controls_flash = {"jump": None, "left": None, "right": None}
controls_display = {"jump": True, "left": True, "right": True}

class Player:
    def __init__(self, s):
        self.s = s
        self.rect = pygame.Rect(*s["player_start_pos"], *s["player_size"])
        self.vy = 0
        self.health = s["initial_health"]
        self.regen = s["health_regen"]
        self.invuln_timer = 0
    def jump(self):
        self.vy = self.s["jump_strength"]
    def update(self):
        self.vy += self.s["gravity"]
        self.rect.y += int(self.vy)
        if self.rect.bottom > self.s["screen_height"]:
            self.rect.bottom = self.s["screen_height"]
            self.vy = 0
    def is_invuln(self):
        return pygame.time.get_ticks() < self.invuln_timer

def start_screen():
    while True:
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN and event.key==pygame.K_SPACE:
                return
        draw_background()
        draw_text("start_title", "Broccoli Runner!")
        draw_text("start_prompt", "Press spacebar to start")
        if controls_display["jump"]: draw_text("control_jump", "Jump: Spacebar")
        if controls_display["left"]: draw_text("control_left", "Move Left: Left Arrow")
        if controls_display["right"]: draw_text("control_right", "Move Right: Right Arrow")
        pygame.display.flip()
        clock.tick(settings["fps"])

def level_loading(level, player):
    for count in range(3, 0, -1):
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks()-start_time < 1000:
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            draw_background()
            draw_text("level_title", f"Level {level+1}")
            draw_text("level_countdown", f"Starting in {count} seconds")
            draw_text("level_health", f"Health: {player.health}")
            pygame.display.flip()
            clock.tick(settings["fps"])

def run_level(level, player):
    lvl_len = settings["level_length"] + level * settings.get("level_length_increase", 0)
    speed = settings["player_speed"] + level * settings["speed_increase"]
    obst_rate = settings["obstacle_spawn_rate"] + level * settings["obstacle_rate_increase"]
    item_rate = settings["item_spawn_rate"] + level * settings["item_rate_increase"]
    progress = 0; obstacles = []; items = []
    while progress < lvl_len and player.health > 0:
        clock.tick(settings["fps"]); progress += speed
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_SPACE and player.rect.bottom>=settings["screen_height"]:
                    player.jump()
                    if controls_display["jump"] and controls_flash["jump"] is None:
                        controls_flash["jump"] = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.rect.x -= settings["ground_control"] if player.rect.bottom>=settings["screen_height"] else settings["air_control"]
            if controls_display["left"] and controls_flash["left"] is None:
                controls_flash["left"] = pygame.time.get_ticks()
        if keys[pygame.K_RIGHT]:
            player.rect.x += settings["ground_control"] if player.rect.bottom>=settings["screen_height"] else settings["air_control"]
            if controls_display["right"] and controls_flash["right"] is None:
                controls_flash["right"] = pygame.time.get_ticks()
        now = pygame.time.get_ticks()
        for k in controls_flash:
            if controls_flash[k] is not None and now - controls_flash[k] > 3000:
                controls_display[k] = False
        # Spawn obstacles with configurable size.
        if random.random() < obst_rate:
            min_w, min_h = settings["obstacle_min_size"]
            max_w, max_h = settings["obstacle_max_size"]
            w = random.randint(min_w, max_w)
            h = w
            obstacles.append(pygame.Rect(settings["screen_width"], settings["screen_height"]-h, w, h))
        # Spawn items with configurable size and vertical spawn position.
        if random.random() < item_rate:
            typ = "healthy" if random.random() < 0.5 else "unhealthy"
            min_iw, min_ih = settings["item_min_size"]
            max_iw, max_ih = settings["item_max_size"]
            w = random.randint(min_iw, max_iw)
            h = w
            y = random.randint(settings["screen_height"]-settings["item_spawn_max_height"],
                               settings["screen_height"]-settings["item_spawn_min_height"])
            items.append({"rect": pygame.Rect(settings["screen_width"], y, w, h), "type": typ})
        obstacles = [o.move(-speed, 0) for o in obstacles if o.right > 0]
        for i in items: i["rect"].x -= speed
        items = [i for i in items if i["rect"].right > 0]
        player.update()
        if not player.is_invuln() and any(player.rect.colliderect(o) for o in obstacles):
            player.health -= settings["health_loss"]
            player.invuln_timer = pygame.time.get_ticks() + settings["invuln_time"]
        new_items = []
        for i in items:
            if player.rect.colliderect(i["rect"]):
                if i["type"]=="healthy":
                    player.regen += 1
                else:
                    player.regen = max(0, player.regen - 1)
            else:
                new_items.append(i)
        items = new_items
        draw_background()
        for o in obstacles:
            if obstacle_sprite:
                spr = pygame.transform.scale(obstacle_sprite, (o.width, o.height))
                screen.blit(spr, o.topleft)
            else:
                pygame.draw.rect(screen, settings["obstacle_color"], o)
        for i in items:
            col = settings["healthy_color"] if i["type"]=="healthy" else settings["unhealthy_color"]
            sprite = healthy_sprite if i["type"]=="healthy" else unhealthy_sprite
            if sprite:
                spr = pygame.transform.scale(sprite, (i["rect"].width, i["rect"].height))
                screen.blit(spr, i["rect"].topleft)
            else:
                pygame.draw.rect(screen, col, i["rect"])
        if not (player.is_invuln() and (pygame.time.get_ticks()//200)%2==0):
            if player_sprite:
                screen.blit(player_sprite, player.rect)
            else:
                pygame.draw.rect(screen, settings["player_color"], player.rect)
        hud = pygame.font.SysFont(None, 24).render(f'Lvl {level+1}  Health: {player.health}  Regen: {player.regen}', True, (255,255,255))
        screen.blit(hud, (10,10))
        if controls_display["jump"]: draw_text("control_jump", "Jump: Spacebar")
        if controls_display["left"]: draw_text("control_left", "Left: Arrow")
        if controls_display["right"]: draw_text("control_right", "Right: Arrow")
        pygame.display.flip()
    player.health += player.regen

player = Player(settings)
start_screen()
for level in range(settings["num_levels"]):
    level_loading(level, player)
    run_level(level, player)
    if player.health <= 0: break
msg = "Game Over" if player.health <= 0 else "You Win!"
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
    draw_background()
    draw_text("end_message", msg)
    pygame.display.flip()
    clock.tick(settings["fps"])
