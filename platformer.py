import os
import sys
import numpy as np
import pygame as pg
from pygame import mixer


# функция для прорисовки текста
def draw_text(text, font, x, y):
    img = font.render(text, True, (0, 5, 5))
    run.screen.blit(img, (x, y))


def load_image(name):
    filename = os.path.join('data', name)
    try:
        image = pg.image.load(filename)
    except pg.error as error:
        raise SystemExit(error)
    return image


def load_level(filename):
    filename = os.path.join('data', filename)
    # Читаем уровень
    with open(filename, 'r') as mapfile:
        levelmap = np.array([list(i) for i in [line.strip() for line in mapfile]])
    return levelmap


def generate_level(level):
    # элементы игрового поля, мобов
    data_lst = list()
    row, col = level.shape
    for y in range(row):
        for x in range(col):
            if level[y, x] == '/':
                data_lst.append(Tile('dirt', x, y))
            elif level[y, x] == '3':
                data_lst.append(Tile('grass_plate_edge_r', x, y))
            elif level[y, x] == '4':
                data_lst.append(Tile('grass_plate_edge_l', x, y))
            elif level[y, x] == '5':
                data_lst.append(Tile('grass_plate', x, y))
            elif level[y, x] == '6':
                data_lst.append(Tile('half', x, y))
            elif level[y, x] == '7':
                data_lst.append(Tile('half2', x, y))
            elif level[y, x] == '#':
                data_lst.append(Tile('wall', x, y))
            elif level[y, x] == 's':
                s = School(x, y)
                run.all_sprites.add(s)
            elif level[y, x] == 'c':
                c = Coin(x, y)
                run.all_sprites.add(c)
                run.coin_group.add(c)
            elif level[y, x] == 'l':
                lava_block = Lava(x, y)
                run.lava_group.add(lava_block)
                run.all_sprites.add(lava_block)
            elif level[y, x] == 'f':
                data_lst.append(Tile('lava_fill', x, y))
            elif level[y, x] == '@':
                enem = Enemy(x, y)
                run.mobs.add(enem)
                run.all_sprites.add(enem)
    return data_lst


class School(pg.sprite.Sprite):
    def __init__(self, pos_x, pos_y):
        pg.sprite.Sprite.__init__(self)
        self.image = load_image('house.png')
        self.rect = self.image.get_rect().move(pos_x * run.tile_width, (pos_y * run.tile_height) - 400)


# разрезание листа с картинками на отдельные кадры
def animasprite(sheet, cols, rows):
    frames = []
    rect = pg.Rect(0, 0, sheet.get_width() // cols, sheet.get_height() // rows)
    for j in range(rows):
        for i in range(cols):
            frame_location = (rect.w * i, rect.h * j)
            frames.append(sheet.subsurface(pg.Rect(frame_location, rect.size)))
    return frames


class Tile(pg.sprite.Sprite):
    def __init__(self, tile_type, pos_x, pos_y):
        super().__init__()
        self.image = run.tile_images[tile_type]
        self.rect = self.image.get_rect().move(run.tile_width * pos_x,
                                               run.tile_height * pos_y)
        self.abs_pos = (self.rect.x, self.rect.y)
        self.out()

    def out(self):
        return self.abs_pos[0], self.abs_pos[1], 70, 70


class Camera:
    def __init__(self, width, height):
        self.camera = pg.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.x + int(run.width / 2.2)
        y = -target.rect.y + int(run.height / 2.2)
        # лимит
        x = min(0, x)  # лево
        y = min(0, y)  # верх
        self.camera = pg.Rect(x, y, self.width, self.height)


class Button:
    def __init__(self, image, pressed):
        self.press_img = load_image(pressed)
        self.img = load_image(image)
        self.image = self.img
        self.clicked = False
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = 430, 530

    def draw(self):
        self.act = False
        # позиция мыши, нажатие левой кнопки мыши
        pos = pg.mouse.get_pos()
        if self.rect.collidepoint(pos):
            self.image = self.press_img
        else:
            self.image = self.img
        run.screen.blit(self.image, self.rect)


class Player(pg.sprite.Sprite):
    def __init__(self, game):
        self.reset(game)

    def reset(self, game):
        pg.sprite.Sprite.__init__(self)
        self.game = game
        # спрайт игрока
        self.stand = load_image('stand.png')
        self.image = self.stand
        self.dead_image = load_image('ded.png')
        self.dead_gravity_count = 0
        self.rect = pg.rect.Rect((5, 880), (70, 148))
        self.on_ground = False
        # трение
        self.friction = -0.12
        # скорость передвижения игрока
        self.vel = vec(0, 0)
        # ускорение
        self.acc = vec(0, 0)
        # переменные для анимации, списки с кадрами
        self.walking = False
        self.walk_r_lst = animasprite(load_image('walk.png'), 4, 1)
        self.walk_l_lst = list()
        for frame in self.walk_r_lst:
            self.walk_l_lst.append(pg.transform.flip(frame, True, False))
        # счетчик кадров
        self.current_frame = 0
        self.last_update = 0
        # в какую сторону смотрит игрок
        self.look = 0

    def jump(self):
        # стоит ли игрок на поверхности
        if self.on_ground:
            self.vel.y = -20

    def update(self):
        self.animate()
        self.acc = vec(0, 0.7)
        # считывание нажатий кнопок передвижения
        if self.game.game_over == 0:
            key = pg.key.get_pressed()
            if key[pg.K_LEFT] or key[pg.K_a]:
                self.acc.x = -0.95
                self.look = 1
            if key[pg.K_RIGHT] or key[pg.K_d]:
                self.acc.x = 0.95
                self.look = 0
            if key[pg.K_SPACE]:
                if self.on_ground:
                    self.game.jump_fx.play()
                self.jump()
            # обновление координат игрока, применение трения
            self.acc.x += self.vel.x * self.friction
            # выравнивание скорости + инерция
            self.vel.x += self.acc.x
            if abs(self.vel.x) < 0.1:
                self.vel.x = 0
            if not self.on_ground:
                self.vel.y += self.acc.y
            self.on_ground = False

            self.rect.y += self.vel.y + 0.5 * self.acc.y
            self.collide(0, self.vel.y)
            self.rect.x += self.vel.x + 0.5 * self.acc.x
            self.collide(self.vel.x, 0)
        elif self.game.game_over == 1:
            if self.look == 0:
                self.image = self.dead_image
            else:
                self.image = pg.transform.flip(self.dead_image, True, False)
            self.dead_gravity_count += 1
            if self.dead_gravity_count <= 17:
                self.rect.y -= 24
            if self.dead_gravity_count > 20:
                if self.dead_gravity_count < 70:
                    self.rect.y += 25

    def collide(self, xvel, yvel):
        for tile in self.game.tiles_group:
            if pg.sprite.collide_rect(self, tile):
                if xvel > 0:
                    self.rect.right = tile.rect.left
                if xvel < 0:
                    self.rect.left = tile.rect.right
                if yvel < 0:
                    self.rect.top = tile.rect.bottom
                    self.vel.y = 0
                if yvel > 0:
                    self.rect.bottom = tile.rect.top
                    self.vel.y = 0
                    self.on_ground = True
                # столкновение с лавой/врагом
                if pg.sprite.spritecollide(self, self.game.mobs, False) or \
                        pg.sprite.spritecollide(self, self.game.lava_group, False):
                    self.game.game_over = 1
                    self.game.game_over_fx.play()

    def animate(self):
        current = pg.time.get_ticks()
        if self.vel.x != 0:
            self.walking = True
        else:
            self.walking = False
        # анимация ходьбы
        if self.walking:
            if current - self.last_update > 190:
                self.last_update = current
                self.current_frame = (self.current_frame + 1) % len(self.walk_r_lst)
                if self.vel.x > 0:
                    self.image = self.walk_r_lst[self.current_frame]
                else:
                    self.image = self.walk_l_lst[self.current_frame]
        if not self.walking:
            if self.look == 0:
                self.image = self.stand
            else:
                self.image = pg.transform.flip(self.stand, True, False)


class Enemy(pg.sprite.Sprite):
    def __init__(self, pos_x, pos_y):
        pg.sprite.Sprite.__init__(self)
        self.image = load_image('enemy.png')
        self.rect = self.image.get_rect().move(run.tile_width * pos_x,
                                               (run.tile_height * pos_y) + 13)
        # списки с кадрами
        self.move_l = animasprite(load_image('enemy_move.png'), 2, 1)
        self.move_r = list()
        for frame in self.move_l:
            self.move_r.append(pg.transform.flip(frame, True, False))
        # счетчик кадров
        self.current_frame = 0
        self.last_update = 0
        # в какую сторону движется/смотрит
        self.look = 2
        self.count = 0

    def update(self):
        self.animate()
        self.rect.x += self.look
        self.count += 1
        if self.count > 90:
            self.look *= -1
            self.count *= -1

    def animate(self):
        current = pg.time.get_ticks()
        if current - self.last_update > 190:
            self.last_update = current
            self.current_frame = (self.current_frame + 1) % len(self.move_l)
            if self.look > 0:
                self.image = self.move_r[self.current_frame]
            else:
                self.image = self.move_l[self.current_frame]


class Coin(pg.sprite.Sprite):
    def __init__(self, pos_x, pos_y):
        pg.sprite.Sprite.__init__(self)
        self.image = load_image('coin1.png')
        self.rect = self.image.get_rect().move(run.tile_width * pos_x,
                                               (run.tile_height * pos_y))
        self.animation = animasprite(load_image('coin.png'), 4, 1)
        self.current_frame = 0
        self.last_update = 0

    def update(self):
        self.animate()

    def animate(self):
        current = pg.time.get_ticks()
        if current - self.last_update > 300:
            self.last_update = current
            self.current_frame = (self.current_frame + 1) % len(self.animation)
            self.image = self.animation[self.current_frame]


class Lava(pg.sprite.Sprite):
    def __init__(self, pos_x, pos_y):
        pg.sprite.Sprite.__init__(self)
        self.image = load_image('lava.png')
        self.rect = self.image.get_rect().move(run.tile_width * pos_x,
                                               (run.tile_height * pos_y))
        self.animation = animasprite(load_image('lava_move.png'), 2, 1)
        self.current_frame = 0
        self.last_update = 0

    def update(self):
        self.animate()

    def animate(self):
        current = pg.time.get_ticks()
        if current - self.last_update > 1300:
            self.last_update = current
            self.current_frame = (self.current_frame + 1) % len(self.animation)
            self.image = self.animation[self.current_frame]


def terminate():
    # определяем отдельную функцию выхода из игры
    pg.quit()
    sys.exit()


# вектор
vec = pg.math.Vector2


def start_screen():
    # заставка
    start_screen_background = load_image('start-screen.jpg')
    run.screen.blit(start_screen_background, (0, 0))
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                terminate()
            elif event.type == pg.KEYDOWN or event.type == pg.MOUSEBUTTONDOWN:
                return  # Начинаем игру
        pg.display.flip()


class Game:
    def __init__(self):
        self.running = True
        pg.init()
        pg.mixer.pre_init(44100, -16, 2, 512)
        mixer.init()
        # параметры для draw_text
        self.font = pg.font.SysFont('Comic Sans', 35)
        pg.display.set_caption('Roota`s adventure')
        size = self.width, self.height = 1200, 800
        self.clock = pg.time.Clock()
        self.screen = pg.display.set_mode(size)
        self.fps = 60
        self.background, self.background_rect = load_image('background.png'), load_image('background.png').get_rect()

    def new(self):
        # Тайлы
        self.tile_images = {
            'wall': load_image('grass.png'), 'dirt': load_image('dark_dirt.png'),
            'grass_plate_edge_r': load_image('grass_edge_plate_right.png'),
            'grass_plate_edge_l': load_image('grass_edge_plate_left.png'),
            'grass_plate': load_image('grass_plate.png'), 'half': load_image('dark_dirt_half.png'),
            'half2': load_image('dark_dirt_half2.png'), 'lava': load_image('lava.png'),
            'lava_fill': load_image('lava_fill.png'), 'school': load_image('house.png')
        }
        # размер тайлов:
        self.tile_width = self.tile_height = 70
        # кнопки
        self.restart_button = Button('try_unpressed.png', 'try_pressed.png')
        self.restart_check = False
        # Группы:
        self.tiles_group = pg.sprite.Group()
        self.all_sprites = pg.sprite.Group()
        self.lava_group = pg.sprite.Group()
        self.coin_group = pg.sprite.Group()
        self.mobs = pg.sprite.Group()
        # звуки
        self.coin_fx = pg.mixer.Sound('data/coin_pick.mp3')
        self.coin_fx.set_volume(0.6)
        self.jump_fx = pg.mixer.Sound('data/jump.mp3')
        self.jump_fx.set_volume(0.05)
        self.game_over_fx = pg.mixer.Sound('data/ded.mp3')
        self.game_over_fx.set_volume(0.8)
        pg.mixer.music.load('data/theme.mp3')
        pg.mixer.music.set_volume(0.4)
        pg.mixer.music.play(-1, 0.0, 5000)
        # генерация уровня
        self.levelmap = load_level('level_1.map')
        data_lst = generate_level(self.levelmap)
        # помещение тайлов в группы
        for tile in data_lst:
            self.all_sprites.add(tile)
            self.tiles_group.add(tile)
        # камера
        self.camera = Camera(len(self.levelmap), len(self.levelmap[0]))
        # переменная для проверки проигрыша, счёт
        self.score = 0
        self.game_over = 0
        # спавн игрока с референсом к классу Game
        self.player = Player(self)
        self.all_sprites.add(self.player)
        self.run()

    def run(self):
        start_screen()
        self.running = True
        while self.running:
            self.playing = True
            while self.playing:
                self.clock.tick(self.fps)
                self.events()
                self.update()
                self.draw()

    def update(self):
        self.all_sprites.update()
        self.camera.update(self.player)

    def events(self):
        # цикл с событиями
        for event in pg.event.get():
            if event.type == pg.QUIT:
                if self.playing:
                    self.playing = False
                self.running = False
            if event.type == pg.MOUSEBUTTONDOWN:
                self.restart_check = True
            else:
                self.restart_check = False
            if pg.Rect.colliderect(self.player.rect, (9630, 750, 150, 100)):
                if self.score == 15:
                    self.playing = False
                    self.running = False

    def draw(self):
        # прорисовка всего
        self.screen.blit(self.background, self.background_rect)
        for sprite in self.all_sprites:
            self.screen.blit(sprite.image, self.camera.apply(sprite))
        # проверка столкновенния с монетами, обновление счетчика
        if pg.sprite.spritecollide(self.player, self.coin_group, True):
            self.score += 1
            self.coin_fx.play()
        draw_text(f'монет:  {str(self.score)} / 15', self.font, 12, 10)
        # рестарт
        if self.game_over == 1:
            self.restart_button.draw()
            if self.restart_check:
                self.player.reset(self)
                self.game_over = 0
        pg.display.flip()


run = Game()
while run.running:
    run.new()
pg.quit()
