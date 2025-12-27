import pygame
import random
import math
import sys
import os

# --- Configuration ---
LOGICAL_WIDTH = 800
LOGICAL_HEIGHT = 600
FPS = 60

# Colors
BLACK = (10, 10, 10)
WHITE = (255, 255, 255)
RED = (255, 60, 60)
GREEN = (50, 205, 50)
DARK_GREEN = (0, 80, 0)
LIME = (100, 255, 100)
YELLOW = (255, 220, 0)
SAND = (238, 214, 175)
SAND_DARK = (180, 160, 120)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
GRAY = (100, 100, 100)
UI_BORDER = (255, 255, 255)

# Battle Box
BOX_W, BOX_H = 300, 240
BOX_RECT = pygame.Rect((LOGICAL_WIDTH - BOX_W)//2, 320, BOX_W, BOX_H)

# --- Asset Management ---

ASSETS = {}

def load_assets():
    """Attempts to load custom images, otherwise sets them to None (triggering fallbacks)."""
    
    # Get the directory where THIS script is located
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()

    print(f"--- CHECKING FOR ASSETS IN: {script_dir} ---")

    def load_safe(name, size=None):
        path = os.path.join(script_dir, name)
        
        if os.path.exists(path):
            try:
                # convert_alpha() requires the display to be initialized first!
                img = pygame.image.load(path).convert_alpha()
                if size:
                    img = pygame.transform.scale(img, size)
                print(f"[FOUND] Loaded custom art: {name}")
                return img
            except pygame.error as e:
                print(f"[ERROR] Found {name} but could not load it: {e}")
                return None
        else:
            print(f"[MISSING] Could not find: {name} (Using default)")
            return None

    # Load images (None if not found)
    ASSETS['player'] = load_safe('player.png', (16, 16))
    ASSETS['boss']   = load_safe('boss.png') 
    ASSETS['thorn']  = load_safe('thorn.png', (16, 32))
    ASSETS['sand']   = load_safe('sand.png') 
    ASSETS['wall']   = load_safe('wall.png', (40, 90))
    ASSETS['beam']   = load_safe('beam.png') 
    print("------------------------------------------------")

# --- Helper Functions ---

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        w, h = font.size(test_line)
        if w < max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    return lines

# --- Visual Effects Classes ---

class Background:
    def __init__(self):
        self.offset_y = 0
        self.offset_x = 0
        self.grid_surf = pygame.Surface((LOGICAL_WIDTH + 40, LOGICAL_HEIGHT + 40), pygame.SRCALPHA)
        # Pre-render grid
        for x in range(0, LOGICAL_WIDTH + 40, 40):
            pygame.draw.line(self.grid_surf, (30, 20, 40), (x, 0), (x, LOGICAL_HEIGHT + 40), 2)
        for y in range(0, LOGICAL_HEIGHT + 40, 40):
            pygame.draw.line(self.grid_surf, (30, 20, 40), (0, y), (LOGICAL_WIDTH + 40, y), 2)
        
    def draw(self, surface):
        self.offset_y = (self.offset_y + 0.5) % 40
        self.offset_x = (self.offset_x + 0.2) % 40
        surface.fill((15, 5, 20))
        surface.blit(self.grid_surf, (-self.offset_x, -self.offset_y))

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color, size, speed_range=4):
        super().__init__()
        self.image = pygame.Surface((size, size))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, speed_range)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.life = random.randint(20, 40)

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        self.life -= 1
        if self.life <= 0:
            self.kill()
        if self.life < 10:
            self.image.set_alpha(self.life * 25)

# --- Game Entities ---

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        
        if ASSETS.get('player'):
            self.image = ASSETS['player']
        else:
            # Fallback Art
            self.image = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.polygon(self.image, RED, [(0, 5), (8, 16), (16, 5), (12, 0), (8, 4), (4, 0)])
            
        self.rect = self.image.get_rect(center=BOX_RECT.center)
        self.speed = 4.5
        self.hp = 20
        self.max_hp = 20
        self.invincible = 0

    def reset(self):
        self.rect.center = BOX_RECT.center
        self.invincible = 0

    def update(self):
        keys = pygame.key.get_pressed()
        move = pygame.math.Vector2(0, 0)
        if keys[pygame.K_LEFT]: move.x = -1
        if keys[pygame.K_RIGHT]: move.x = 1
        if keys[pygame.K_UP]: move.y = -1
        if keys[pygame.K_DOWN]: move.y = 1
        
        if move.length() > 0:
            move = move.normalize() * self.speed
            self.rect.x += move.x
            self.rect.y += move.y

        self.rect.clamp_ip(BOX_RECT.inflate(-8, -8))

        if self.invincible > 0:
            self.invincible -= 1
            if self.invincible % 4 < 2:
                self.image.set_alpha(100)
            else:
                self.image.set_alpha(255)
        else:
            self.image.set_alpha(255)

    def take_damage(self, amount):
        if self.invincible == 0:
            self.hp -= amount
            self.invincible = 60
            return True
        return False

class Boss:
    def __init__(self):
        self.hp = 100
        self.max_hp = 100
        self.shake = 0
        self.float_offset = 0
        self.float_speed = 0.05
        
        # Check if we have custom art
        self.custom_image = ASSETS.get('boss')
        if self.custom_image:
            # Resize if it's wildly too big, otherwise keep resolution
            w, h = self.custom_image.get_size()
            if w > 400:
                scale = 400 / w
                self.custom_image = pygame.transform.scale(self.custom_image, (int(w*scale), int(h*scale)))

    def draw(self, surface):
        if self.shake > 0:
            offset_x = random.randint(-4, 4)
            self.shake -= 1
        else:
            offset_x = 0
        
        self.float_offset += self.float_speed
        hover_y = math.sin(self.float_offset) * 10
        
        center_x = LOGICAL_WIDTH // 2 + offset_x
        base_y = 80 + hover_y

        if self.custom_image:
            # Draw Custom Image
            img_rect = self.custom_image.get_rect(center=(center_x, base_y + 100))
            surface.blit(self.custom_image, img_rect)
        else:
            # Draw Fallback Procedural Art
            pts = [(center_x, base_y), (center_x - 120, base_y + 200), (center_x + 120, base_y + 200)]
            pygame.draw.polygon(surface, DARK_GREEN, pts) 
            pts_in = [(center_x, base_y + 5), (center_x - 110, base_y + 195), (center_x + 110, base_y + 195)]
            pygame.draw.polygon(surface, GREEN, pts_in)

            # Texture Lines
            for i in range(1, 7):
                y_level = base_y + (i * 28)
                width_at_level = i * 35
                pygame.draw.line(surface, DARK_GREEN, (center_x - width_at_level//2, y_level), (center_x + width_at_level//2, y_level), 2)
                step = 40
                offset = 20 if i % 2 == 0 else 0
                start_x = int(center_x - width_at_level//2)
                for bx in range(start_x + offset, int(center_x + width_at_level//2), step):
                    pygame.draw.line(surface, DARK_GREEN, (bx, y_level), (bx, y_level - 28), 2)

            # Eye
            eye_y = base_y + 80
            pulse = abs(math.sin(self.float_offset * 3)) * 4
            glow_surf = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 255, 0, 50), (50, 50), 38 + pulse)
            surface.blit(glow_surf, (center_x - 50, eye_y - 50))
            pygame.draw.circle(surface, YELLOW, (center_x, eye_y), 32)
            pygame.draw.circle(surface, BLACK, (center_x, eye_y), 32, 3)
            # Pupil
            pygame.draw.ellipse(surface, BLACK, (center_x - 8, eye_y - 20, 16, 20), 3)
            pygame.draw.line(surface, BLACK, (center_x, eye_y), (center_x, eye_y + 20), 4)
            pygame.draw.line(surface, BLACK, (center_x - 12, eye_y + 5), (center_x + 12, eye_y + 5), 4)

        # Health Bar
        self.draw_health(surface)

    def draw_health(self, surface):
        bar_w = 400
        bar_h = 18
        x = (LOGICAL_WIDTH - bar_w) // 2
        y = 30
        pygame.draw.rect(surface, (40, 0, 0), (x, y, bar_w, bar_h))
        ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surface, RED, (x, y, bar_w * ratio, bar_h))
        pygame.draw.rect(surface, GRAY, (x, y, bar_w, bar_h), 2)
        font = pygame.font.SysFont("Arial", 16, bold=True)
        text = font.render("CACTUS PYRAMID", True, (200, 200, 200))
        surface.blit(text, (x, y + 20))

# --- Projectile Classes ---

class Thorn(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.w, self.h = 16, 32
        
        if ASSETS.get('thorn'):
            self.image = ASSETS['thorn']
        else:
            # Fallback
            self.image = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            pygame.draw.polygon(self.image, DARK_GREEN, [(0,0), (self.w,0), (self.w//2, self.h)])
            pygame.draw.polygon(self.image, GREEN, [(2,0), (self.w-2,0), (self.w//2, self.h-2)])
            pygame.draw.polygon(self.image, LIME, [(4,0), (self.w-4,0), (self.w//2, self.h-5)])
        
        self.rect = self.image.get_rect(midbottom=(random.randint(BOX_RECT.left, BOX_RECT.right), BOX_RECT.top))
        self.speed = random.randint(4, 7)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > BOX_RECT.bottom:
            self.kill()

class Beam(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.w, self.h = 40, BOX_H
        # Make a surface for the beam
        self.image = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(random.randint(BOX_RECT.left, BOX_RECT.right - 40), BOX_RECT.top))
        self.timer = 0
        self.warn_time = 50
        self.active_time = 30
        self.state = "warn"

    def update(self):
        self.timer += 1
        self.image.fill((0,0,0,0))
        
        if self.timer < self.warn_time:
            # Warning
            alpha = 80 + int(math.sin(self.timer * 0.5) * 40)
            pygame.draw.rect(self.image, (255, 0, 0, alpha), (0, 0, self.w, self.h))
            pygame.draw.rect(self.image, RED, (0,0,self.w,self.h), 1)
            cx = self.w // 2
            pygame.draw.line(self.image, RED, (cx, 10), (cx, self.h - 20), 2)
            pygame.draw.circle(self.image, RED, (cx, self.h - 10), 2)
            
        elif self.timer < self.warn_time + self.active_time:
            self.state = "active"
            
            if ASSETS.get('beam'):
                # Custom Beam Texture
                # Stretch the beam texture to fill the rect
                stretched = pygame.transform.scale(ASSETS['beam'], (self.w, self.h))
                self.image.blit(stretched, (0,0))
            else:
                # Fallback Beam
                pygame.draw.rect(self.image, CYAN, (5, 0, self.w-10, self.h))
                pygame.draw.rect(self.image, WHITE, (12, 0, self.w-24, self.h))
                pygame.draw.rect(self.image, (0, 200, 255, 100), (0, 0, self.w, self.h), 4)
                for y in range(0, self.h, 20):
                    pygame.draw.line(self.image, BLACK, (12, y), (self.w-12, y), 1)

        else:
            self.kill()

class SandPuff(pygame.sprite.Sprite):
    def __init__(self, from_left):
        super().__init__()
        size = random.randint(20, 35)
        
        if ASSETS.get('sand'):
            # Scale the custom sand particle
            self.image = pygame.transform.scale(ASSETS['sand'], (size, size))
        else:
            # Fallback
            self.image = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            pygame.draw.circle(self.image, SAND, (c, c), c)
            pygame.draw.circle(self.image, SAND_DARK, (c, c), c, 2)
            for _ in range(3):
                ox = random.randint(4, size-4)
                oy = random.randint(4, size-4)
                pygame.draw.circle(self.image, SAND_DARK, (ox, oy), 2)

        self.rect = self.image.get_rect()
        self.rect.y = random.randint(BOX_RECT.top, BOX_RECT.bottom)
        
        if from_left:
            self.rect.x = BOX_RECT.left - 20
            self.speed = random.randint(4, 8)
        else:
            self.rect.x = BOX_RECT.right + 20
            self.speed = random.randint(-8, -4)
            
        self.wobble_offset = random.random() * 10

    def update(self):
        self.rect.x += self.speed
        self.rect.y += math.sin(self.rect.x * 0.05 + self.wobble_offset) * 1.5
        if self.rect.right < BOX_RECT.left - 50 or self.rect.left > BOX_RECT.right + 50:
            self.kill()

class CactusWall(pygame.sprite.Sprite):
    def __init__(self, x, is_top):
        super().__init__()
        self.w, self.h = 40, 90
        
        if ASSETS.get('wall'):
            self.image = ASSETS['wall']
        else:
            # Fallback
            self.image = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            rect_color = GREEN
            rib_color = DARK_GREEN
            pygame.draw.rect(self.image, rect_color, (0, 0, self.w, self.h))
            for i in range(5, self.w, 10):
                pygame.draw.line(self.image, rib_color, (i, 0), (i, self.h), 2)
                for j in range(10, self.h, 20):
                    pygame.draw.line(self.image, BLACK, (i, j), (i + (4 if i < self.w/2 else -4), j - 2), 1)
            pygame.draw.rect(self.image, rib_color, (0, 0, self.w, self.h), 3)

        self.rect = self.image.get_rect()
        self.rect.x = x
        if is_top: 
            self.rect.top = BOX_RECT.top
        else: 
            self.rect.bottom = BOX_RECT.bottom

    def update(self):
        self.rect.x -= 4
        if self.rect.right < BOX_RECT.left:
            self.kill()

# --- Engine ---

class Game:
    def __init__(self):
        pygame.init()
        
        # 1. Initialize Display FIRST
        self.screen = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
        pygame.display.set_caption("Cactus Pyramid Boss Fight")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        
        # 2. Load Assets SECOND (now that display exists)
        load_assets()
        
        # Fonts
        self.font_big = pygame.font.SysFont("Impact", 60)
        self.font_ui = pygame.font.SysFont("Verdana", 22)
        self.font_small = pygame.font.SysFont("Verdana", 18)
        self.font_dmg = pygame.font.SysFont("Courier New", 34, bold=True)
        self.font_dialogue = pygame.font.SysFont("Consolas", 20)
        
        # Components
        self.bg = Background()
        self.player = Player()
        self.boss = Boss()
        self.projectiles = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()
        
        # State
        self.reset_game_state()

    def reset_game_state(self):
        self.state = "MAIN_MENU" # MAIN_MENU, FIGHT, PAUSE, GAME_OVER, VICTORY
        self.sub_state = "MENU" # MENU, AIM, DEFEND
        self.menu_index = 0
        self.pause_index = 0
        
        self.player.reset()
        self.player.hp = self.player.max_hp
        self.boss.hp = self.boss.max_hp
        self.projectiles.empty()
        self.particles.empty()
        
        self.attack_phase = 0
        self.turn_timer = 0
        self.dialogue = "Cactus Pyramid looms over you."
        self.dialogue_lines = []
        self.update_dialogue_lines()
        
        self.slider_val = 0
        self.slider_dir = 1
        self.display_dmg = None
        self.display_dmg_timer = 0

    def update_dialogue_lines(self):
        max_w = BOX_RECT.width - 30 
        self.dialogue_lines = wrap_text(self.dialogue, self.font_dialogue, max_w)

    def spawn_particles(self, x, y, color, count=10):
        for _ in range(count):
            p = Particle(x, y, color, random.randint(3, 6))
            self.particles.add(p)

    def draw_centered(self, text, font, y, color=WHITE):
        s = font.render(text, True, color)
        self.screen.blit(s, (LOGICAL_WIDTH//2 - s.get_width()//2, y))

    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

    def handle_input(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            
            if event.type == pygame.KEYDOWN:
                # MENU
                if self.state == "MAIN_MENU":
                    if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                        self.menu_index = 1 - self.menu_index
                    if event.key == pygame.K_z or event.key == pygame.K_RETURN:
                        if self.menu_index == 0:
                            self.state = "FIGHT"
                            self.sub_state = "MENU"
                        else:
                            pygame.quit(); sys.exit()

                # PAUSE
                elif self.state == "PAUSE":
                    if event.key == pygame.K_ESCAPE: self.state = "FIGHT"
                    if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                        self.pause_index = 1 - self.pause_index
                    if event.key == pygame.K_z:
                        if self.pause_index == 0: self.state = "FIGHT"
                        else: self.reset_game_state()

                # FIGHT
                elif self.state == "FIGHT":
                    if event.key == pygame.K_ESCAPE: self.state = "PAUSE"; self.pause_index = 0
                    
                    if self.sub_state == "MENU":
                        if event.key == pygame.K_z:
                            self.sub_state = "AIM"
                            self.slider_val = 0
                            self.slider_dir = 12
                            self.dialogue = "Strike perfectly!"
                            self.update_dialogue_lines()

                    elif self.sub_state == "AIM":
                        if event.key == pygame.K_z:
                            # Attack Logic
                            center = LOGICAL_WIDTH // 2
                            hit_x = (LOGICAL_WIDTH//2 - 250) + self.slider_val
                            dist = abs(center - hit_x)
                            
                            dmg = 0
                            if dist < 25: 
                                dmg = random.randint(22, 28)
                                self.spawn_particles(center, 200, YELLOW, 15)
                            elif dist < 120:
                                dmg = random.randint(10, 15)
                                self.spawn_particles(center, 200, WHITE, 8)
                            else:
                                dmg = 0
                            
                            self.boss.hp -= dmg
                            if dmg > 0: self.boss.shake = 10
                            
                            self.display_dmg = str(dmg) if dmg > 0 else "MISS"
                            self.display_dmg_timer = 60
                            
                            if self.boss.hp <= 0:
                                self.state = "VICTORY"
                            else:
                                self.sub_state = "DEFEND"
                                self.player.reset()
                                self.projectiles.empty()
                                self.attack_phase = (self.attack_phase % 4) + 1
                                self.turn_timer = 0
                                msgs = {1: "Thorns fall from above!", 2: "Watch the warning signals!", 3: "A sandstorm blinds you!", 4: "Weave through the cactus!"}
                                self.dialogue = msgs.get(self.attack_phase, "")
                                self.update_dialogue_lines()

                # END
                elif self.state in ["VICTORY", "GAME_OVER"]:
                    if event.key == pygame.K_z:
                        self.reset_game_state()

    def update(self):
        self.bg.draw(self.screen)
        self.particles.update()

        if self.state == "FIGHT":
            if self.display_dmg_timer > 0: self.display_dmg_timer -= 1
            
            if self.sub_state == "AIM":
                self.slider_val += self.slider_dir
                if self.slider_val > 500 or self.slider_val < 0:
                    self.slider_dir *= -1
            
            elif self.sub_state == "DEFEND":
                self.player.update()
                self.projectiles.update()
                self.turn_timer += 1
                
                # Boss Logic
                if self.attack_phase == 1:
                    if self.turn_timer % 8 == 0: self.projectiles.add(Thorn())
                    if self.turn_timer > 300: self.end_player_turn()
                elif self.attack_phase == 2:
                    if self.turn_timer % 40 == 0 and self.turn_timer < 250: self.projectiles.add(Beam())
                    if self.turn_timer > 350: self.end_player_turn()
                elif self.attack_phase == 3:
                    if self.turn_timer % 4 == 0: self.projectiles.add(SandPuff(self.turn_timer % 8 < 4))
                    if self.turn_timer > 300: self.end_player_turn()
                elif self.attack_phase == 4:
                    if self.turn_timer % 45 == 0:
                        is_top = random.choice([True, False])
                        self.projectiles.add(CactusWall(BOX_RECT.right + 20, not is_top))
                    if self.turn_timer > 400: self.end_player_turn()

                # Collisions
                hits = pygame.sprite.spritecollide(self.player, self.projectiles, False)
                for h in hits:
                    hit_active = True
                    if isinstance(h, Beam) and h.state != "active": hit_active = False
                    
                    if hit_active:
                        if self.player.take_damage(2):
                            self.spawn_particles(self.player.rect.centerx, self.player.rect.centery, RED)
                            if self.player.hp <= 0: self.state = "GAME_OVER"

    def end_player_turn(self):
        self.sub_state = "MENU"
        self.dialogue = "Cactus Pyramid waits."
        self.update_dialogue_lines()
        self.projectiles.empty()

    def draw(self):
        if self.state == "MAIN_MENU":
            self.draw_centered("CACTUS PYRAMID", self.font_big, 150, GREEN)
            c1 = YELLOW if self.menu_index == 0 else GRAY
            c2 = YELLOW if self.menu_index == 1 else GRAY
            self.draw_centered("START GAME", self.font_ui, 350, c1)
            self.draw_centered("QUIT", self.font_ui, 400, c2)
            self.draw_centered("[ Arrows to Move | Z to Select ]", self.font_small, 500, GRAY)

        elif self.state in ["FIGHT", "PAUSE", "GAME_OVER", "VICTORY"]:
            self.boss.draw(self.screen)
            pygame.draw.rect(self.screen, BLACK, BOX_RECT)
            pygame.draw.rect(self.screen, UI_BORDER, BOX_RECT, 4)
            self.particles.draw(self.screen)
            
            if self.sub_state == "DEFEND":
                self.projectiles.draw(self.screen)
                self.screen.blit(self.player.image, self.player.rect)
            
            elif self.sub_state == "MENU":
                self.screen.blit(self.player.image, self.player.rect)
                btn_rect = pygame.Rect(BOX_RECT.left + 20, BOX_RECT.top + 20, 140, 40)
                color = ORANGE if (pygame.time.get_ticks()//500)%2==0 else RED
                pygame.draw.rect(self.screen, color, btn_rect, 2)
                txt = self.font_ui.render("FIGHT [Z]", True, color)
                txt_rect = txt.get_rect(center=btn_rect.center)
                self.screen.blit(txt, txt_rect)
                
            elif self.sub_state == "AIM":
                bar_rect = pygame.Rect(LOGICAL_WIDTH//2 - 250, BOX_RECT.top - 70, 500, 30)
                pygame.draw.rect(self.screen, BLACK, bar_rect)
                pygame.draw.rect(self.screen, WHITE, bar_rect, 3)
                pygame.draw.rect(self.screen, GREEN, (LOGICAL_WIDTH//2 - 25, bar_rect.y+2, 50, 26))
                cx = bar_rect.x + self.slider_val
                pygame.draw.rect(self.screen, WHITE, (cx, bar_rect.y - 5, 6, 40))

            if self.state not in ["GAME_OVER", "VICTORY"]:
                text_y = BOX_RECT.top + 80 if self.sub_state == "MENU" else BOX_RECT.top + 20
                for i, line in enumerate(self.dialogue_lines):
                    s = self.font_dialogue.render("* " + line if i == 0 else "  " + line, True, WHITE)
                    self.screen.blit(s, (BOX_RECT.left + 20, text_y + (i * 25)))

            if self.display_dmg_timer > 0:
                y_off = (60 - self.display_dmg_timer)
                s = self.font_dmg.render(self.display_dmg, True, RED)
                self.screen.blit(s, (LOGICAL_WIDTH//2 - s.get_width()//2, BOX_RECT.top - 120 - y_off))

            pygame.draw.rect(self.screen, RED, (BOX_RECT.left + 50, BOX_RECT.bottom + 15, self.player.max_hp * 6, 20))
            pygame.draw.rect(self.screen, YELLOW, (BOX_RECT.left + 50, BOX_RECT.bottom + 15, self.player.hp * 6, 20))
            hp_txt = self.font_small.render(f"HP {self.player.hp} / {self.player.max_hp}", True, WHITE)
            self.screen.blit(hp_txt, (BOX_RECT.left + 50 + (self.player.max_hp*6) + 15, BOX_RECT.bottom + 15))
            lbl = self.font_small.render("LV 1", True, WHITE)
            self.screen.blit(lbl, (BOX_RECT.left, BOX_RECT.bottom + 15))

            if self.state == "PAUSE":
                overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0,0,0,180))
                self.screen.blit(overlay, (0,0))
                self.draw_centered("- PAUSED -", self.font_big, 150)
                c1 = YELLOW if self.pause_index == 0 else GRAY
                c2 = YELLOW if self.pause_index == 1 else GRAY
                self.draw_centered("RESUME", self.font_ui, 300, c1)
                self.draw_centered("QUIT TO TITLE", self.font_ui, 350, c2)

            if self.state == "GAME_OVER":
                self.draw_centered("GAME OVER", self.font_big, 200, RED)
                self.draw_centered("Stay determined... Press Z", self.font_ui, 300, WHITE)

            if self.state == "VICTORY":
                self.draw_centered("VICTORY!", self.font_big, 200, YELLOW)
                self.draw_centered("The desert falls silent. Press Z", self.font_ui, 300, WHITE)

        pygame.display.flip()

if __name__ == "__main__":
    Game().run()