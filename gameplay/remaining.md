Major (core gameplay missing)                                                                                     
                                                                                                                    
  1. Dynamic price function (README.md:204-234)                                                                     
  The README specifies MARKET_PARAMS with per-resource shape functions (linear, sqrt, log, sq, log10), base, I0, T, 
  below_target, above_target. Prices should recompute from inventory each turn. Currently MarketPrices is a fixed   
  BaseModel and MARKET_PARAMS doesn't exist anywhere in src/. Market interleaving uses fixed prices and never shifts
   them mid-turn — so the "one unit at a time, price may shift between rounds" mechanic is inert.                   
                                                                                                                  
  2. Market inventory starts at I0 = 10,000 (README.md:190)                                                         
  "Every product (and fertilizer) starts the game with a market inventory of I0 = 10,000 units." Fixtures start at
  0; no production initializer sets 10,000. The whole price function depends on this anchor.                        
                                                                                                                  
  3. Ongoing crop scheduled production (README.md:125)                                                              
  "Ongoing crops (tomato, strawberry): Scheduled production happens at fixed intervals. The base yield is 1 per   
  scheduled production. If the plant is fertilized AND watered that day, yield is doubled to 2." water.py:44        
  explicitly defers ongoing-crop bonus to "production time", but nothing implements production time. refresh_plant
  only handles miss counters + decay. Result: tomato/strawberry plants never accrue yield — they sit at             
  yield_units=0 until decay.                                                                                      

  4. Animal scheduled production payout (README.md:75-80, plan: D2)                                                 
  "On a scheduled production day, if the animal is fed, the entire banked bonus is added to that production's yield
  (in addition to the base 1) and the bank resets to 0." pending_care_bonus banking is implemented in               
  refresh_animal.py:46, but the payout on first_yield_day + k*interval doesn't exist anywhere. ANIMAL_CONFIG carries
   first_yield_day + interval but nothing reads them. Animals never produce eggs/milk/wool.                         
                                                                                                                  
  5. Animal HARVEST (README.md:69)                                                                                  
  "HARVEST — Collect the eggs/milk/wool produced by the animal." harvest.py:31 only handles PlantState — non-plant
  tiles return {"crop": None, "yield": 0}. There's no path to harvest yield_units off an AnimalState into the shed. 
                                                                                                                  
  6. DROP action (README.md:50)                                                                                     
  "DROP — orthogonally adjacent to the shed, dump the active farmer/hand's entire current inventory into the shed."
  Not in src/models/action.py (only PICKUP and PLACE exist). PLACE covers shed drop with a count arg, but DROP (dump
   entire inventory) is a distinct action per the README.                                                         
                                                                                                                    
  Medium (documented but deferred)                                                                                  
   
  7. Per-player observation extraction (README.md:256-279)                                                          
  The agent-facing observation has private: {...} (one player's private state). The full-game GameState holds     
  privates: list[PrivateState]. No builder extracts the per-agent view, so the env can't be handed to an agent yet. 
                                                                                                                  
  8. Market refresh post-turn (README.md:244)                                                                       
  "Market refresh — modify the price of items on the market based on sells from previous turn." This is the       
  price-function recompute; tied to gap #1.                                                                         
                                                                                                                  
  9. Sell-at-floor behavior (README.md:196)                                                                         
  "If the sell price has been driven down to $1 (the price floor), the unit is still purchased but is not added to
  market inventory." sell_one adds to inventory unconditionally.                                                    
                                                                                                                  
  10. Buy vs sell price asymmetry (README.md:202)                                                                   
  "Buy price is quoted at the post-buy inventory, sell price at the pre-sell inventory." Currently both read the  
  same fixed market.prices; coupled to gap #1.                                                                      
                                                                                                                  
  Smaller / config plumbing                                                                                         
                                                                                                                  
  11. Configuration flow + starting money (README.md:347-361)                                                       
  Constants exist in src/utils/config.py (STARTING_MONEY=3000, BOARD_SIZE=10, EPISODE_STEPS=720, etc.) but nothing
  reads an env.configuration dict to override them per episode. Fixtures also use money=0.0 rather than             
  STARTING_MONEY. The seed config parameter for deterministic episode generation isn't wired into Environment.    
                                                                                                                    
  12. fertilizer_available type mismatch (README.md:322)                                                            
  README observation format says "fertilizer_available": bool; the model has it as int. Minor, but surfaces when the
   observation builder (gap #7) lands.                                                                              
                                                                                                                  
  13. Action validation phase (README.md:238)                                                                       
  "Action validation — verify action legality" is listed as a distinct step. Currently each action module silently
  no-ops on illegal inputs, which is functionally equivalent — but there's no explicit pre-dispatch validation pass.
                   