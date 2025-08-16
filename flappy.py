import tkinter as tk
import random
import os

WIDTH, HEIGHT = 480, 640
GROUND_H = 64
BIRD_SIZE = 26
GRAVITY = 0.5
FLAP_VY = -8.5
PIPE_W = 70
PIPE_GAP = 150
PIPE_SPEED = 3.5
SPAWN_EVERY = 1400
FPS_MS = 16

HS_FILE = "flappy_highscore.txt"

SKY = "#87ceeb"
PIPE_FILL = "#9ca3af"
PIPE_OUTL = "#4b5563"
GROUND = "#228B22"
BIRD = "#ff6347"

class FlappyGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Flappy Square — Python/tkinter")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=SKY, highlightthickness=0)
        self.canvas.pack()

        self.ui_score = self.canvas.create_text(WIDTH//2, 28, fill="#111", font=("Segoe UI", 18, "bold"), text="0")
        self.ui_high  = self.canvas.create_text(WIDTH-80, 28, fill="#333", font=("Segoe UI", 12, "bold"), text="High: 0")

        self.ground1 = self.canvas.create_rectangle(0, HEIGHT-GROUND_H, WIDTH, HEIGHT, fill=GROUND, outline="")
        self.ground2 = self.canvas.create_rectangle(WIDTH, HEIGHT-GROUND_H, WIDTH*2, HEIGHT, fill=GROUND, outline="")

        self.bird = self.canvas.create_rectangle(80, HEIGHT//2, 80+BIRD_SIZE, HEIGHT//2+BIRD_SIZE, fill=BIRD, outline="")

        self.vy = 0.0
        self.pipes = []
        self.running = False
        self.gameover = False
        self.score = 0
        self.high = self.load_high()
        self.update_high_ui()
        self._scored = set()

        self.message = self.canvas.create_text(WIDTH//2, HEIGHT//2 - 32, fill="#000",
                                               font=("Segoe UI", 16, "bold"),
                                               text="Нажми Space, чтобы играть")
        self.submsg  = self.canvas.create_text(WIDTH//2, HEIGHT//2 + 4,  fill="#333",
                                               font=("Segoe UI", 12),
                                               text="Управление: Space — прыжок, P — пауза, R — рестарт")

        root.bind("<space>", self.on_space)
        root.bind("<Escape>", lambda e: root.destroy())
        root.bind("<KeyPress>", self.on_keypress)

        self.spawn_after_id = None
        self.loop()

    def on_keypress(self, e: tk.Event):
        ks = (e.keysym or "").lower()
        kc = int(e.keycode) if hasattr(e, "keycode") else -1
        if ks == "p" or kc == 80:
            self.toggle_pause(e)
            return
        if ks == "r" or kc == 82:
            self.on_restart(e)
            return

    def start(self):
        if self.gameover:
            return
        if not self.running:
            self.running = True
            self.canvas.itemconfig(self.message, text="")
            self.canvas.itemconfig(self.submsg, text="")
            self.schedule_spawn()

    def on_space(self, _):
        if not self.running and not self.gameover:
            self.start()
        if self.running and not self.gameover:
            self.vy = FLAP_VY

    def on_restart(self, _):
        self.reset()

    def toggle_pause(self, _):
        if self.gameover:
            return
        self.running = not self.running
        if self.running:
            self.canvas.itemconfig(self.message, text="")
            self.canvas.itemconfig(self.submsg, text="")
            self.schedule_spawn()
        else:
            if self.spawn_after_id:
                self.root.after_cancel(self.spawn_after_id)
                self.spawn_after_id = None
            self.canvas.itemconfig(self.message, text="Пауза")
            self.canvas.itemconfig(self.submsg, text="Нажми P, чтобы продолжить")

    def reset(self):
        self.running = False
        self.gameover = False
        self.score = 0
        self.vy = 0
        self._scored.clear()
        self.canvas.coords(self.bird, 80, HEIGHT//2, 80+BIRD_SIZE, HEIGHT//2+BIRD_SIZE)
        for top, bot in self.pipes:
            self.canvas.delete(top)
            self.canvas.delete(bot)
        self.pipes.clear()
        if self.spawn_after_id:
            self.root.after_cancel(self.spawn_after_id)
            self.spawn_after_id = None
        self.canvas.itemconfig(self.ui_score, text="0")
        self.canvas.itemconfig(self.message, text="Нажми Space, чтобы играть")
        self.canvas.itemconfig(self.submsg, text="Управление: Space — прыжок, P — пауза, R — рестарт")

    def schedule_spawn(self):
        if self.spawn_after_id:
            self.root.after_cancel(self.spawn_after_id)
        self.spawn_after_id = self.root.after(SPAWN_EVERY, self.spawn_pipe)

    def spawn_pipe(self):
        if not self.running:
            return
        gap_y = random.randint(120, HEIGHT - GROUND_H - 120)
        top_h = gap_y - PIPE_GAP//2
        bot_y = gap_y + PIPE_GAP//2
        top = self.canvas.create_rectangle(WIDTH, 0, WIDTH + PIPE_W, top_h, fill=PIPE_FILL, outline=PIPE_OUTL)
        bot = self.canvas.create_rectangle(WIDTH, bot_y, WIDTH + PIPE_W, HEIGHT - GROUND_H, fill=PIPE_FILL, outline=PIPE_OUTL)
        self.pipes.append((top, bot))
        self.schedule_spawn()

    def loop(self):
        if self.running and not self.gameover:
            self.step_physics()
            self.move_pipes()
            self.move_ground()
            self.check_collisions()
        self.root.after(FPS_MS, self.loop)

    def step_physics(self):
        self.vy += GRAVITY
        x1, y1, x2, y2 = self.canvas.coords(self.bird)
        ny = y1 + self.vy
        floor = HEIGHT - GROUND_H - BIRD_SIZE
        if ny > floor:
            ny = floor
            self.vy = 0
            self.set_gameover()
        self.canvas.coords(self.bird, x1, ny, x1 + BIRD_SIZE, ny + BIRD_SIZE)

    def move_pipes(self):
        to_remove = []
        bx1, _, _, _ = self.canvas.coords(self.bird)
        for i, (top, bot) in enumerate(self.pipes):
            self.canvas.move(top, -PIPE_SPEED, 0)
            self.canvas.move(bot, -PIPE_SPEED, 0)
            _, _, x2, _ = self.canvas.coords(top)
            if x2 < 0:
                to_remove.append(i)
            if top not in self._scored and x2 < bx1:
                self._scored.add(top)
                self.score += 1
                self.canvas.itemconfig(self.ui_score, text=str(self.score))
        for idx in reversed(to_remove):
            top, bot = self.pipes[idx]
            self._scored.discard(top)
            self.canvas.delete(top)
            self.canvas.delete(bot)
            del self.pipes[idx]

    def move_ground(self):
        self.canvas.move(self.ground1, -PIPE_SPEED, 0)
        self.canvas.move(self.ground2, -PIPE_SPEED, 0)
        x1, _, x2, _ = self.canvas.coords(self.ground1)
        if x2 <= 0:
            self.canvas.move(self.ground1, WIDTH*2, 0)
        x1, _, x2, _ = self.canvas.coords(self.ground2)
        if x2 <= 0:
            self.canvas.move(self.ground2, WIDTH*2, 0)

    def check_collisions(self):
        bx1, by1, bx2, by2 = self.canvas.coords(self.bird)
        for top, bot in self.pipes:
            if self.rects_intersect((bx1, by1, bx2, by2), self.canvas.coords(top)) or \
               self.rects_intersect((bx1, by1, bx2, by2), self.canvas.coords(bot)):
                self.set_gameover()
                return

    @staticmethod
    def rects_intersect(a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def set_gameover(self):
        if self.gameover:
            return
        self.gameover = True
        self.running = False
        if self.score > self.high:
            self.high = self.score
            self.save_high(self.high)
            self.update_high_ui()
        self.canvas.itemconfig(self.message, text="Игра окончена")
        self.canvas.itemconfig(self.submsg, text="Нажми R, чтобы сыграть ещё раз")

    def update_high_ui(self):
        self.canvas.itemconfig(self.ui_high, text=f"High: {self.high}")

    def load_high(self):
        try:
            if os.path.exists(HS_FILE):
                with open(HS_FILE, "r", encoding="utf-8") as f:
                    return int(f.read().strip() or 0)
        except Exception:
            pass
        return 0

    def save_high(self, value):
        try:
            with open(HS_FILE, "w", encoding="utf-8") as f:
                f.write(str(value))
        except Exception:
            pass

def main():
    root = tk.Tk()
    game = FlappyGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()
