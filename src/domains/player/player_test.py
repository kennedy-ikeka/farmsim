from tests.fixtures import _make_env
from src.domains.player.player import Player
from src.models.action import MoveActionState, PassActionState


def _make_player(farmer=(5, 5), hands=None, rows=10, cols=10):
    """Build a Player (a RealityState) whose farms/player match env's player 0.

    Mirrors how `Environment.step` constructs per-player `Player` views from
    the shared state, so `get_valid_actions` sees the same farm shapes.
    """
    env = _make_env(rows=rows, cols=cols, farmer=farmer, hands=hands)
    shared = env.state.model_dump(exclude={"privates", "player"}, mode="json")
    return Player(**shared, player=0, private=env.state.privates[0])


def _types(actions):
    return sorted(a.type for a in actions)


class TestGetValidActions:
    """Tests for `Player.get_valid_actions`."""

    def test_includes_pass(self):
        player = _make_player(farmer=(5, 5))
        types = _types(player.get_valid_actions())
        assert "PASS" in types

    def test_center_farmer_no_hands(self):
        """Pass + the four in-bounds farmer moves, nothing else."""
        player = _make_player(farmer=(5, 5), hands=[])
        types = _types(player.get_valid_actions())
        assert types == ["EAST", "NORTH", "PASS", "SOUTH", "WEST"]

    def test_corner_farmer_only_two_moves(self):
        player = _make_player(farmer=(0, 0), hands=[])
        types = _types(player.get_valid_actions())
        assert types == ["EAST", "PASS", "SOUTH"]

    def test_includes_moves_for_each_hand(self):
        """With one hand at the NW corner and one at the SE corner, the aggregated
        move set is the union of the farmer's and each hand's valid directions."""
        player = _make_player(farmer=(5, 5), hands=[[0, 0], [9, 9]])
        types = _types(player.get_valid_actions())
        # farmer (5,5) -> all four; hand [0,0] -> EAST,SOUTH; hand [9,9] -> NORTH,WEST
        # union across all three units is still all four directions + PASS
        assert set(types) == {"EAST", "NORTH", "PASS", "SOUTH", "WEST"}

    def test_counts_reflect_every_unit(self):
        """The flat list contains one MoveActionState per valid (unit, direction)
        pair — 4 for the farmer at center + 2 per corner hand = 8 moves, plus 1 pass."""
        player = _make_player(farmer=(5, 5), hands=[[0, 0], [9, 9]])
        actions = player.get_valid_actions()
        move_count = sum(1 for a in actions if isinstance(a, MoveActionState))
        pass_count = sum(1 for a in actions if isinstance(a, PassActionState))
        assert move_count == 8  # 4 (farmer) + 2 (hand 0) + 2 (hand 1)
        assert pass_count == 1

    def test_edge_farmer_with_edge_hand(self):
        player = _make_player(farmer=(0, 5), hands=[[9, 0]])
        actions = player.get_valid_actions()
        # farmer at top edge -> EAST, SOUTH, WEST (no NORTH); hand at [9,0] -> EAST, NORTH
        types = _types(actions)
        assert "NORTH" in types  # contributed by the hand
        assert "SOUTH" in types  # contributed by the farmer
        # the farmer cannot go NORTH, the hand cannot go SOUTH — but each direction
        # is present at least once because some unit can make that move.
        assert set(types) == {"EAST", "NORTH", "PASS", "SOUTH", "WEST"}
        # 3 farmer moves + 2 hand moves + 1 pass = 6 actions total
        assert len(actions) == 6