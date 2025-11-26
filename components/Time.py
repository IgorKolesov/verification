class Time:
    def __init__(self, start_tick: int = 0):
        self.current_tick = start_tick

    def tick(self):
        self.current_tick += 1

    def reset(self):
        self.current_tick = 0

    def get(self) -> int:
        return self.current_tick

    def __str__(self):
        return f"Tick: {self.current_tick}"