from __future__ import annotations

class UCB1:
    def __init__(self):
        self.n = 0
        self.k = []
        self.cnts = {}
        self.rew = {}

    def add_arm(self, arm: str):
        if arm not in self.cnts:
            self.cnts[arm] = 0
            self.rew[arm] = 0.0
            self.k.append(arm)

    def select(self):
        import math
        self.n += 1
        vals = []
        for a in self.k:
            if self.cnts[a] == 0:
                vals.append((a, float("inf")))
                continue
            avg = self.rew[a] / max(1, self.cnts[a])
            bonus = (2 * math.log(self.n) / self.cnts[a]) ** 0.5
            vals.append((a, avg + bonus))
        if not vals:
            return None
        vals.sort(key=lambda x: x[1], reverse=True)
        return vals[0][0]

    def update(self, arm: str, reward: float):
        if arm not in self.cnts:
            self.add_arm(arm)
        self.cnts[arm] += 1
        self.rew[arm] += float(reward)
