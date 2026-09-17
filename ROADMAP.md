# Sn1p3rM0nk3y roadmap

A vision-and-input bot for Bloons TD 6. What to build, in what order, and what to ignore until later.

**Target map for v1–v2:** Monkey Meadow, Hard Standard (autostart off).
**North star:** an offline planner produces a full-game action list that passes every round on paper; an executor plays that list between rounds through a game harness.

Optional later: a companion app beside windowed BTD6, with plan UI and a local KoboldCpp **personality** (constraints), never a click-brain.

---

## Architecture

```
[optional LLM] --> PlanConstraint
                         |
Planner  --plan-->  Executor  --actions-->  GameHarness  -->  BTD6 window
              ^                    |
              |                    +-- play button, failed placements
              |
        SimulatedHarness  (no window; same Observation / Action)
```

| Piece | Job |
| --- | --- |
| **GameHarness** | Window, clicks, screen ID, occupancy, cash ledger, round clock. `reset` / `observe` / `step`. |
| **SimulatedHarness** | Same API, no pyautogui. Used to pre-play a plan. |
| **Planner** | Deterministic search until every round passes the meters. |
| **Executor** | Replay the plan between rounds. Repair if `step` fails. |
| **Catalog** | Tower stats, upgrades, crosspath rules, `rounds.json`. |
| **PlanConstraint** | Shrinks the legal buy set. Gamemodes and “human play” both live here. |
| **LLM (later)** | Emits a personality / constraint JSON. Does not click. Planner still must pass meters or the personality is rejected. |

**Actions (mid-level, not raw clicks):** `PlaceTower`, `PlaceHero`, `Upgrade`, `Wait`, `StartRound` (press play). Later: `SetTargeting`, `UseAbility`, `Sell` if a mode allows it.

**Observation** is three layers, never one blob:

1. **Sensed** — play button idle vs running; did the last purchase land; screen (in-game / pause / game over).
2. **Believed** — placed towers, upgrades, occupancy, cash ledger, round index.
3. **Forecast** — remaining rounds from `rounds.json` (groups, RBE, cash).

Brains / planners must not import window capture. They only see `Observation` and query helpers (`placement_candidates`, costs, legal upgrades). `step()` stays off that query interface.

---

## Locked rules

These are decided. Don’t reopen them unless a version fails.

### No OCR

Drop `MoneyReader` / EasyOCR from the live loop. Do not read cash or round digits.

### Cash is a ledger

```
cash = starting_cash(gamemode)
      + sum(rounds.json income for completed rounds that actually ran)
      - sum(verified purchase costs)
```

`rounds.json` cash looks like `"$20 + $101"` (pop cash + end bonus). Credit it when the round **finishes**. Ignore farms, Benjamin, and Monkey Knowledge (underestimate is safe).

**Failed placements must not debit cash.**

**Mode caveats:** CHIMPS / Impoppable start at round **6** — do not credit rounds 1–5. Deflation has almost no further income. Half Cash halves the ledger. Sandbox: `cash = inf`. Apopalypse: out of scope (no idle play button).

### The harness owns the round clock

Autostart **off**. Pixel-identify the play triangle (idle) vs fast-forward (running), same style as `PAGE_IDENTIFIER_POINTS`.

Shop → press play → wait until idle → `round += 1`, add income → shop again.

### Actions only between rounds

The planner and executor never buy mid-round. Abilities that must be timed *during* a round (First Strike on the MOAB, Bomb Blitz, etc.) are a later executor feature, not v1–v2.

### Checkpoints, not generic DPS mix

Each round is **meters**: grouped RBE, camo RBE, lead RBE, MOAB RBE, plus binary properties (can anyone interact with camo / lead / purple / black).

- **Hard fail:** a property nobody can interact with.
- **Soft fail:** a meter is below `margin × round_rbe` (start around `1.3`). Margin stands in for spacing; we are **not** simulating spacing.
- Do **not** maximize every meter every shop. Min-cost to pass the current fail, with dual-use bias toward later hard fails.
- Ice / glue / farm / village are **not** combat DPS. Don’t use `stat or 1`.

Clear rate:

- Grouped: `(damage × min(pierce, typical_group) × projectiles) / cooldown`
- MOAB / single-target: `damage / cooldown`
- `0` if the tower cannot pop that bloon type

**DDT** is not a fifth vague meter. It is camo + lead + black (and fast). A plan that “has camo” and “has lead” on different towers can still leak DDTs.

### Effective DPS (coverage)

```
effective = catalog_clear_rate × (flow_points_in_range / scale)
```

Placement and planning happen together. Wiki DPS is a ceiling.

### Open-loop plan, then execute

Search until **every** remaining round passes. If the model dies on a later camo spike, fail pre-play. Same map + same catalog + no extra constraints → same plan every time.

### Heroes (v1–v2)

Do not pretend a level-1 hero is a 5-xxx Super. XP (hence level) changes every round even if you buy nothing. `hero_properties.json` is only cost / range / footprint.

Until there is a per-level stat table + XP-by-round (deterministic if you don’t leak):

- Place the hero, occupy space, record it on `placed_towers`.
- Credit **binary** coverage only when it is true at level 1 (e.g. Sauda camo).
- Combat DPS: conservative curve or **zero**. Benjamin / Geraldo / Corvus are not `damage / cooldown` at all.

### LLM personality (later, not a click-brain)

Planner/executor stay deterministic. KoboldCpp (local OpenAI-compatible API) returns constraint JSON. If no meter-passing plan exists, reject the personality.

### Explicitly out of scope until “Later”

Spacing / clumping, extra income, bloon push, abilities during rounds, village/alch buffs, farms as economy, LOS/walls, lives HUD, Monkey Knowledge, selling.

---

## Version 1 — Harness and executor

**Goal:** play a known action list on Meadow, between rounds, with a correct cash ledger and no OCR.

### Build

- `actions.py`, `observation.py`, `catalog.py`
- `harness.py` — nav, occupancy, place/upgrade, play-button clock, ledger
- `executor.py` — shop listed steps, `StartRound`, wait for idle
- Keep `interaction.py` / `vision.py` (screen ID only). Remove money OCR from the live path
- Heroes go on `placed_towers`
- Do not debit cash or paint occupancy until placement looks successful

### Prove it

Hand-write a tiny Meadow plan (dart + hero + a couple upgrades). Several rounds with no cash/tower desync. Then delete `BloonsBrain.main()`.

### Not in v1

Planner, meters, multi-path, LOS, constraints, UI.

---

## Version 2 — Offline planner (single path)

**Goal:** SimulatedHarness + planner produce a Meadow plan that passes meters through a round cap (e.g. 40 or 80), then the v1 executor plays it.

### Build

- `SimulatedHarness`
- Parse `rounds.json` groups into property flags + RBE slices
- Effective DPS from flow-point coverage
- Search: first failing round → dual-use-biased buy → re-scan until the cap passes
- Optional small beam if greedy dies on a known spike
- `main.py`: plan offline → if pass, execute

### Prove it

Pre-play never hard-fails camo/lead/MOAB inside the cap. Live Meadow matches the plan. Second run is identical.

### Not in v2

Four-lane maps, LOS, human-play LLM, farms, ability micro.

---

## Version 3 — Multi-path maps

**Goal:** track data and meters understand more than one lane.

Upgrade `processing_tools/track_flow_points.py` and `path_points.json`:

```json
{
  "track_name": "Ouch",
  "spawn": { "mode": "cycle", "carry_across_rounds": true },
  "paths": [
    { "id": 1, "path_corners": [], "flow_points": [] },
    { "id": 2, "path_corners": [], "flow_points": [] }
  ]
}
```

- Editor: **N** starts the next lane; **S** saves all; color per path
- Legacy `flow_points` = one path
- #OUCH: cycle `1→2→3→4`, continues across rounds (restart snaps to path 1)
- Checkpoints **per-lane** / worst-lane. Placement maximizes **min** coverage across lanes
- Re-trace Meadow as a one-path file so there is a single code path

### Prove it

Meadow still plans. A four-path dummy refuses “all towers on one street” even if global RBE looks fine.

---

## Later

| Item | Notes |
| --- | --- |
| **LOS / effective area** | Raycast through `wall_mask`. Snipers are almost pure LOS. Precompute coverage maps. |
| **`PlanConstraint` / `HumanPlayConstraint`** | Unique towers, max copies, random bans, seeded runs. Must still pass meters. |
| **LLM personality + KoboldCpp** | One local HTTP call per game → constraint JSON. Optional; app plays unconstrained if Kobold is down. |
| **Companion app** | Window beside BTD6: plan list, next actions, harness screen/round/ledger, settings, built-in track tools. Then an installer. Windowed BTD6. Windows-first. NK ToS still apply for anyone else running it. |
| **Hero level tables** | XP-by-round × per-level stats. Until then, conservative/binary only. |
| **Farms, villages, alch, stall** | Own terms, not fake DPS. |
| **Abilities / targeting / sell** | Mid-round executor actions. Needed for real CHIMPS win conditions. |
| **DDT / Super Ceramic / Fortified as first-class** | See gap list below. |
| **MK, Deflation, Half Cash, ABR** | Ledger and round table variants. |

---

## Suggested layout

```
catalog.py
actions.py
observation.py
harness.py
sim_harness.py
executor.py
planner.py
constraints.py           # later
app/                     # later companion UI
interaction.py
vision.py
processing_tools/track_flow_points.py
data/rounds.json
data/tracks/<map>/path_points.json
main.py
```

---

## What the current bot actually does

`bloons.py` is one class: window I/O, placement, a greedy scorer, and `main()`. Live loop: identify screen, `find_best_action`, place/upgrade, hover banana farms. It reached **round 103** on Meadow — a real result — with no round clock.

`find_best_action` multiplies: flow-point count × coverage-gap vs static `COVERAGE_RATIOS` × duplicate penalty × (DPS/cost) × discounted upgrade-tree DPS. Cash is EasyOCR every few seconds fused with an estimate that **only subtracts purchases**.

That is the donor for nav, masks, and hotkeys — not the policy.

---

## Gap dive — current heuristic

Concrete misses in today’s `BloonsBrain`, including things a human CHIMPS guide would call load-bearing. Grouped by how soon the new design should care.

### Already slated to fix (v1–v2)

- No round index; unused `rounds.json`
- DPS = `damage * pierce * projectiles / cooldown` (Ice 0-0-0 looks like a carry)
- `or 1` invents DPS for Farm/Village
- Static camo/lead “balance” on round 3
- Hero not on `placed_towers`; no level curve
- Failed placements still debit cash and paint occupancy
- Cash OCR; estimate never adds round income
- Coverage `.get("lead")` vs StrEnum `"Lead"` in unused `calculate_global_dps`
- Base range only for placement scoring

### Meters the planner must grow into (v2+, or CHIMPS will lie)

These are why “pass RBE + camo + lead + MOAB” is not enough to match how people actually plan.

| Gap | Why it matters | What humans / other bots do |
| --- | --- | --- |
| **DDT** | Camo + lead + **black**, and fast. Split coverage (village camo + bomb lead) still leaks r90. | Treat DDT as its own hard fail from 90, 95, 99. |
| **Super Ceramics (r81+)** | Ceramic HP jumps; high-pierce low-damage spam falls off. CHIMPS guides say don’t leave junk T1s into late game. | Separate ceramic/MOAB-class meters after 80; prefer a few T5s + support. |
| **Fortified** | HP multiplier, not an immunity. Your `CoverageType` has no Fortified. | Scale MOAB/ceramic meters (×2 shell) on Fortified* types already in `rounds.json`. |
| **Density vs total RBE** | r63 is three tight ceramic waves. Same RBE spread out is easy. Margin `1.3` is a blunt instrument. | Optional “tight wave” flag on known rounds (63, 76, 78, 98) with a higher margin. |
| **Children of blimps** | r40 RBE 616 includes the ceramics inside. Grouped DPS that never cracks the MOAB still “passes” MOAB RBE if you only sum. | Split **shell HP** (single-target) vs **inside RBE** (grouped cleanup). |
| **Decamo vs seeing camo** | Shimmer / MIB / Etienne UAV vs a ninja that shoots camo. Different solutions. | Property “camo is handled” can be decamo **or** camo DPS. |
| **Zebra / black / white** | Zebra is both. Explosion can’t pop black; energy can’t pop purple. | Parse `rounds.json` types (`CamoGreen`, `FortifiedCamoRegrowCeramic`) into a property set, not one tag. |
| **Regrow** | r76 / r78. Slow popping on-track regenerates. | Don’t model regen in v2; know those rounds need faster grouped clear (higher margin). |
| **Purple** | Immune to energy/fire/frost. r25, r78, r95. | You have the enum; the live scorer barely uses it as a round trigger. |
| **Bloon speed** | Coverage count ≠ time-on-target. Pinks and DDTs spend less time in the same circle. | Later: weight flow points by 1/speed. V2 ignores (locked: no push/spacing). |
| **Entrance vs exit** | Front of track = more remaining length. Equal flow-point counts treat the exit as equal. | Weight samples by remaining path index (cheap, worth doing in v2). |

Community “key rounds” the checkpoint list should include as named fails, not just first-camo/first-lead: **24, 28, 40, 59 (camo lead), 63, 76, 78, 80 (ZOMG), 90 (DDT), 95, 98, 99, 100 (BAD)**. BAD is also immune to slow — stall wincons die there.

### Placement and tower-shaped holes (v2–v3 / later)

The current scorer uses one circle and “how many path dots are inside.” That is wrong for a lot of the roster:

- **Spike Factory / Perma-Spike** — win condition on many CHIMPS maps. Must sit at the **exit**, not the densest mid-track. Your farm hover is the only “support” behavior and it isn’t this.
- **Mortar / Ace / Heli / Dartling** — not a range circle (global, pursuit, reticle). `base_range: 0` mortars and Psi’s `1000000` range will break naive coverage.
- **Sniper** — range is not the story; **LOS** is (`wall_mask`).
- **Beast Handler** — merge/power, not a 0-0-0 DPS stick.
- **Alch / Village** — buff other towers. CHIMPS guides treat Jungle Drums + Berserker Brew as load-bearing. Zero in the current score except fake 1 DPS.
- **Glue / Ice** — stall and immunities (frozen bloons). BAD ignores slow.
- **Submerge (sub 0-2-2)** — camo via a specific upgrade, not `base_sees_camo`.
- **Water drain (#OUCH)** — map action, not a tower.

**Targeting** (`First` / `Last` / `Strong` / `Close`) is never set. Strong vs MOABs, Close for spikes, First for glue. Without a `SetTargeting` action, even a correct tower is the wrong gun.

### Economy and modes

- Monkey Knowledge (free dart, +$200, discounts) desyncs wiki costs. Testing should assume **MK off** or a MK profile.
- CHIMPS: no income heroes/farms, no selling, no continues, start round 6.
- Deflation: lump cash, then zero income — the ledger must not keep adding `rounds.json` cash.
- ABR: different round table than `rounds.json`.
- Reverse: flow points must run **exit → entrance** or time-on-target is backwards.

### Executor / “playing the game”

Between-rounds-only cannot express:

- Ability timings (First Strike, Ground Zero, Sabotage, Naval Tactics)
- Mid-round retarget (Pop and Awe, Heli pursuit)
- Sell-to-afford (illegal in CHIMPS, useful on Hard Standard)
- Fast-forward vs 1× for ability cooldowns
- Geraldo shop / Corvus spells (those *are* the hero)

CHIMPS “win conditions” on the wiki are almost all **T5 + support + abilities** (Perma-Spike, Glaive Lord, BEZ, Solver, Comanche…). A v2 meter planner will buy *something* that passes paper RBE; it will not discover Perma-Spike at the exit unless placement rules and support terms exist.

### Data and tooling

- `DAMAGE_TYPE_BY_COVERAGE` is missing Fire, Acid, and several wiki types
- Upgrade scrape uses `Damage` / `Cooldown` keys inconsistently; many upgrades are flavor text only
- `PIXELS_PER_BLOONS_UNIT = 5.375` is a magic constant
- Track tool hardcodes `"Monkey Meadow"` while pointed at other folders
- Only three maps have masks; thumbnail table lists ~70
- `rounds.json` `rbe` is a string with commas (`"1,157"`)

### What other bots do instead

Most public BTD6 bots **don’t** live-score DPS. They OCR or count the round and run a **human script** (Jazzmoon, Randy-Hodges, btd6farmer). j-miet’s bot reads **upgrade panel text** rather than cash. ry-lu’s CHIMPS AI used a **mod** plus a net that predicts “will this layout leak,” not pierce math.

Your planner is more ambitious than a script. It will stay honest only if meters grow toward **DDT, fortified HP, blimp shell vs insides, and tower-shaped placement** — and if you accept that v2 Meadow Hard is the test, not Black Border #OUCH.

---

## Current code (donor, not policy)

- `bloons.py` — god class + old `main()`
- Cash OCR in `money_reader.py` / `vision.py` (delete from live path in v1)
- Placement: one `flow_points` polyline + land/water/track masks (Meadow, In The Loop, Alpine Run)
- `track_flow_points.py` — single polyline
- `hero_properties.json` — cost/range/footprint only
- `banned_towers = []` in `main()` — stub for `PlanConstraint`
