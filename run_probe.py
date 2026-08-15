"""Probe: BASIC against the REAL market (real prices + inventory)."""
from collections import Counter

from src.domains.environment.town import Town
from src.domains.farm import Farm
from src.domains.market import Market
from src.domains.player.player import Player
from src.domains.environment.environment import Environment
from src.models.player import PlayerConfig, ScoreWeights, ResourceWeights, PrivateState, ShedState, SeedsState
from src.models.market import MarketInventory, MarketPrices
from src.models.game import SharedRealityState
from src.utils.config import EPISODE_STEPS

SHED_FIELDS = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER","GOOSE","COW","SHEEP"]
SEED_FIELDS = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON"]

PRICES = dict(WHEAT=26, CARROT=36, TOMATO=60, STRAWBERRY=128, MELON=256,
              EGG=50, MILK=169, WOOL=206, FERTILIZER=100)
INV = {k: 9999 for k in PRICES}
INV["FERTILIZER"] = 10000


def _tiles():
    t = [[None]*10 for _ in range(10)]
    for r in range(5, 10):
        for c in range(10):
            t[r][c] = "LOCKED"
    for r in range(10):
        for c in range(5, 10):
            t[r][c] = "LOCKED"
    return t


def make_env(players, money=3000, farmer=(4,4), config=None):
    def farm():
        return Farm(money=money, tiles=_tiles(), farmer=list(farmer),
                     hands=[], unlocked_quadrants=["NW"], hires_today=0)
    shed = ShedState(**{k: 0 for k in SHED_FIELDS})
    seeds = SeedsState(**{k: 0 for k in SEED_FIELDS})
    cfg = config or PlayerConfig()
    privates = [PrivateState(shed=shed, seeds=seeds, inventories=[], config=cfg)
               for _ in range(players)]
    inv = MarketInventory(**INV)
    prices = MarketPrices(**PRICES)
    state = SharedRealityState(
        remainingOverageTime=60, step=0, day=0, hour=0, player=0,
        farms=[farm() for _ in range(players)],
        privates=privates,
        market=Market(inventory=inv, prices=prices),
        town=Town(unlocked_shops=[]),
    )
    return Environment(state=state, seed=42)


def run(cfg, label):
    env = make_env(players=2, config=cfg)
    log = []
    real = Player.basic_play
    def spy(self):
        s = real(self)
        log.append((self.step, self.player, s.farmer.type, [m.type for m in s.market]))
        return s
    Player.basic_play = spy
    # simulate calls build() which uses flat-1 prices — patch build to preserve our market.
    Environment.build = lambda self, *a, **kw: None
    result = env.simulate(steps=EPISODE_STEPS, player_configs=[cfg, cfg])
    Player.basic_play = real

    print(f"\n=== {label} ===")
    print(f"balances: {result.balances}  winner={result.winner}")
    ft, mt = Counter(), Counter()
    for step, p, ftype, mtypes in log:
        if p != 0:
            continue
        ft[ftype] += 1
        for m in mtypes:
            mt[m] += 1
    print("farmer:", ft.most_common())
    print("market:", mt.most_common())
    print("first 10 player-0 steps:")
    for step, p, ftype, mtypes in log[:20]:
        if p != 0:
            continue
        print(f"  step {step}: farmer={ftype} market={mtypes}")


run(PlayerConfig(method="BASIC",
                 score_weights=ScoreWeights(COST=1, REWARD=100),
                 resource_weights=ResourceWeights(MONEY=1e9, LAND=0, SEED=0, ANIMAL=0, HAND=0, STEP=1)),
    "A: MONEY=1e9, LAND=0")

run(PlayerConfig(method="BASIC",
                 score_weights=ScoreWeights(COST=1, REWARD=100),
                 resource_weights=ResourceWeights(MONEY=1, STEP=1, SEED=1, LAND=1, ANIMAL=1, HAND=1)),
    "B: all weights=1 (real prices)")