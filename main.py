from src.domains.player.player import Player
from src.models.player import PlayerConfig, PrivateState, ScoreWeights


def main(obs):
    private = PrivateState(
        config=PlayerConfig(
            method="BASIC", 
            score_weights=ScoreWeights(COST=1.1, REWARD=1),
        )
    )

    p = Player(**(obs | {"private": private}))
    state = p.play().to_kaggle()
    return state

if __name__ == "__main__":
    main()
