                         ┌───────────────┐
                         │  GAME CONFIG  │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ ENVIRONMENT   │
                         │   SIMULATOR   │
                         └───────┬───────┘
                                 │
                            GAME STATE
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
                 ▼               ▼               ▼
              FARMERS          MARKET          WORLD
                 │               │               │
                 │               │               │
                 └───────┬───────┴───────────────┘
                         │
                         ▼
                    OBSERVATIONS
                         │
                         ▼
                  STRATEGIC AGENT
                         │
                 ┌───────┴────────┐
                 │                │
                 ▼                ▼
             POLICY          CANDIDATE
                              ACTIONS
                                 │
                                 ▼
                         ┌───────────────┐
                         │ LOOKAHEAD     │
                         │ SIMULATOR     │
                         └───────┬───────┘
                                 │
                        N hypothetical worlds
                                 │
                                 ▼
                         OUTCOME SCORING
                                 │
                                 ▼
                            ACTION
                                 │
                                 ▼
                         REAL SIMULATOR
                                 │
                                 ▼
                            NEW STATE
                                 │
                                 ▼
                             NEXT TICK


1. GameState
       ↓
2. Action model
       ↓
3. Event model
       ↓
4. Environment.step()
       ↓
5. Deterministic game mechanics
       ↓
6. Random/stochastic mechanics
       ↓
7. Market simulator
       ↓
8. Rule-based baseline agents
       ↓
9. Replay system
       ↓
10. Tournament runner
       ↓
11. Your LLM policy
       ↓
12. Lookahead simulator
       ↓
13. Self-play
       ↓
14. Opponent pool
       ↓
15. Training/distillation