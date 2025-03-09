import pygame, sys, json, random
with open("settings.json") as f: settings = json.load(f)
pygame.init()
screen = pygame.display.set_mode((settings["screen_width"], settings["screen_height"]))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

# Control flash tracking: each control is displayed until used, then stays for 3 sec and vanishes.
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
        screen.fill(settings["bg_color"])
        title = font.render("Broccoli Runner!", True, (255,255,255))
        prompt = font.render("Press spacebar to start", True, (255,255,255))
        screen.blit(title, ((settings["screen_width"]-title.get_width())//2, 100))
        screen.blit(prompt, ((settings["screen_width"]-prompt.get_width())//2, 150))
        # Show control hints until they are used
        if controls_display["jump"]:
            txt = font.render("Jump: Spacebar", True, (255,255,255))
            screen.blit(txt, (100, 250))
        if controls_display["left"]:
            txt = font.render("Move Left: Left Arrow", True, (255,255,255))
            screen.blit(txt, (100, 280))
        if controls_display["right"]:
            txt = font.render("Move Right: Right Arrow", True, (255,255,255))
            screen.blit(txt, (100, 310))
        pygame.display.flip()
        clock.tick(settings["fps"])

def level_loading(level, player):
    # Countdown from 3 to 1, displaying level and current health.
    for count in range(3, 0, -1):
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks()-start_time < 1000:
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            screen.fill(settings["bg_color"])
            lvl_txt = font.render(f"Level {level+1}", True, (255,255,255))
            count_txt = font.render(f"Starting in {count} seconds", True, (255,255,255))
            health_txt = font.render(f"Health: {player.health}", True, (255,255,255))
            screen.blit(lvl_txt, ((settings["screen_width"]-lvl_txt.get_width())//2, 100))
            screen.blit(count_txt, ((settings["screen_width"]-count_txt.get_width())//2, 150))
            screen.blit(health_txt, ((settings["screen_width"]-health_txt.get_width())//2, 200))
            pygame.display.flip()
            clock.tick(settings["fps"])

def run_level(level, player):
    lvl_len = settings["level_length"] + level * settings.get("level_length_increase", 0)
    speed = settings["player_speed"] + level * settings["speed_increase"]
    obst_rate = settings["obstacle_spawn_rate"] + level * settings["obstacle_rate_increase"]
    item_rate = settings["item_spawn_rate"] + level * settings["item_rate_increase"]
    progress = 0; obstacles = []; items = []
    while progress < lvl_len and player.health > 0:
        dt = clock.tick(settings["fps"]); progress += speed
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_SPACE and player.rect.bottom>=settings["screen_height"]:
                    player.jump()
                    if controls_display["jump"] and controls_flash["jump"] is None:
                        controls_flash["jump"] = pygame.time.get_ticks()
        # Handle left/right movement continuously
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.rect.x -= settings["ground_control"] if player.rect.bottom>=settings["screen_height"] else settings["air_control"]
            if controls_display["left"] and controls_flash["left"] is None:
                controls_flash["left"] = pygame.time.get_ticks()
        if keys[pygame.K_RIGHT]:
            player.rect.x += settings["ground_control"] if player.rect.bottom>=settings["screen_height"] else settings["air_control"]
            if controls_display["right"] and controls_flash["right"] is None:
                controls_flash["right"] = pygame.time.get_ticks()
        # Update control flashes (hide after 3 seconds)
        now = pygame.time.get_ticks()
        for k in controls_flash:
            if controls_flash[k] is not None and now-controls_flash[k]>3000:
                controls_display[k] = False
        # Spawn obstacles & items
        if random.random() < obst_rate:
            w, h = random.randint(20,70), random.randint(20,70)
            obstacles.append(pygame.Rect(settings["screen_width"], settings["screen_height"]-h, w, h))
        if random.random() < item_rate:
            typ = "healthy" if random.random() < 0.5 else "unhealthy"
            items.append({"rect": pygame.Rect(settings["screen_width"], random.randint(settings["screen_height"]-200, settings["screen_height"]-50), 20, 20), "type": typ})
        obstacles = [o.move(-speed,0) for o in obstacles if o.right>0]
        for i in items: i["rect"].x -= speed
        items = [i for i in items if i["rect"].right>0]
        player.update()
        # Collision with obstacles (if not invulnerable)
        if not player.is_invuln() and any(player.rect.colliderect(o) for o in obstacles):
            player.health -= settings["health_loss"]
            player.invuln_timer = pygame.time.get_ticks()+settings["invuln_time"]
        # Collision with items (adjust regen)
        new_items = []
        for i in items:
            if player.rect.colliderect(i["rect"]):
                if i["type"]=="healthy":
                    player.regen += 1
                else:
                    player.regen = max(0,player.regen-1)
            else:
                new_items.append(i)
        items = new_items
        # Drawing
        screen.fill(settings["bg_color"])
        for o in obstacles: pygame.draw.rect(screen, settings["obstacle_color"], o)
        for i in items:
            col = settings["healthy_color"] if i["type"]=="healthy" else settings["unhealthy_color"]
            pygame.draw.rect(screen, col, i["rect"])
        if not (player.is_invuln() and (pygame.time.get_ticks()//200)%2==0):
            pygame.draw.rect(screen, settings["player_color"], player.rect)
        hud = font.render(f'Lvl {level+1}  Health: {player.health}  Regen: {player.regen}', True, (255,255,255))
        screen.blit(hud, (10,10))
        # Show control hints if still active
        y = 40
        if controls_display["jump"]:
            txt = font.render("Jump: Spacebar", True, (255,255,255)); screen.blit(txt, (10,y)); y+=20
        if controls_display["left"]:
            txt = font.render("Left: Arrow", True, (255,255,255)); screen.blit(txt, (10,y)); y+=20
        if controls_display["right"]:
            txt = font.render("Right: Arrow", True, (255,255,255)); screen.blit(txt, (10,y)); y+=20
        pygame.display.flip()
    player.health += player.regen

player = Player(settings)
start_screen()
for level in range(settings["num_levels"]):
    level_loading(level, player)
    run_level(level, player)
    if player.health <= 0: break
msg = "Game Over" if player.health<=0 else "You Win!"
while True:
    for event in pygame.event.get():
        if event.type==pygame.QUIT: pygame.quit(); sys.exit()
    screen.fill(settings["bg_color"])
    text = font.render(msg, True, (255,255,255))
    screen.blit(text, ((settings["screen_width"]-text.get_width())//2, (settings["screen_height"]-text.get_height())//2))
    pygame.display.flip()
    clock.tick(settings["fps"])
