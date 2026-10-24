# NIKKE REBORN — Card Pack Plan

*Status: planning · drafted 2025-10-21 · updated 2026-10-24 (the ELYSION base pack stands at 19 — the *Bibli* reserve top-up is dropped, base packs carry launch-day NIKKEs only) · the `cards/Alpha` set is a dev prototype (see data notes)*

Twelve card packs (expansions) covering every NIKKE banner release from Nov 2022 to Oct 2026, in release order. **Packs 1–3 are the base packs: they carry the 63 NIKKEs released with the game (all 2022-11-04 per the [Release dates](#release-dates) section), grouped by manufacturer — ELYSION (19) first, as it carries the set's face, then TETRA (22), MISSILIS (22) — and release before every other pack. Every pack carries 20–30 NIKKEs (ELYSION stands at 19 — a base pack carries launch-day NIKKEs only).** Each NIKKE in a pack gets the three card variants — static, idle animated, and a skill-cut full art where the NIKKE has a cut-in (all roster NIKKEs are SR/SSR and do).

## How a pack is built

| Roster slot | What it is | Source |
|---|---|---|
| **New** | the pack's featured NIKKEs — every banner first appearance in the pack's window, in release order | banner history |
| **Re-appears** | NIKKEs whose (older) banner the game re-ran concurrently with the pack's banners — the "previous packs re-appear" rule | banner re-runs |
| **Base forms** | a featured skin's base model, where it exists in the viewer database (e.g. base *Mast* beside *Mast: Romantic Maid*) — only NIKKEs who debuted after the launch; every launch NIKKE prints in the base packs | viewer database |
| **Launch** | the 63 NIKKEs released with the game (2022-11-04) — no banner first appearance in the tracker (the standard launch banners are untracked), so they enter the plan only via the base packs (1–3), where they release before every other pack | release dates |
| **Reserve** | a NIKKE drawn from the commons reserve to hold the roster at ≥ 20 (precedent: the alternatives below) | commons reserve |

- Packs are grouped by release season; seasons are merged until the roster lands at 20–30 NIKKEs. Packs 1–3 (the base packs) have no banner window — every launch NIKKE shares the 2022-11-04 release date, so they are grouped by **manufacturer** instead — ELYSION first (it carries the set's face, Rapi, who leads it as 0001), then TETRA and MISSILIS + the 6 PILGRIM fairy-tale NIKKEs by launch-line size — and ordered **SSR → SR → R, ties by NIKKE id** (Rapi excepted as the face card). Concurrent banners are never split across packs (2B/A2, the NERV trios).
- Nothing is double-counted inside a pack (a NIKKE listed as a re-appearance is not also listed as a base form); the same NIKKE may appear in several packs — re-appears and base forms are often re-lists of a pack's own predecessors (base *Helm* in Abyss re-lists Genesis' Helm; *Dorothy* in Outbreak re-lists Genesis' Dorothy). Launch NIKKEs print once, in the base packs.
- Pack slots are filled per the pack rarity config (mostly common): the **commons reserve** (below) supplies repeat-print filler, while the pack's new NIKKEs anchor the top tiers and re-appears/base forms print mid-rarity.

## Sources

- Banner history: <https://lootandwaifus.com/nikke-banner-history/> (GLOBAL server list — 165 banners: 120 first appearances + 45 re-runs, Nov 2022 – Oct 2026). Fetched 2025-10-21; raw parse kept in `database/banners.json`. Portrait paths resolve to the viewer model ids (`mi_c405_00` → `c405`); four legacy-portrait banners were resolved against the database (c103, c105, c322, c515).
- Renderable roster: `database/characters.json` — 201 NIKKE skins `nikke-viewer` can render (`c`-prefixed ids, as used by card JSON `id` fields); the launch roster's manufacturer split (TETRA 21 / ELYSION 19 / MISSILIS 16 / PILGRIM 6) also comes from here. 2026-10-24: five stale entries dropped (Siren c340 — the mined alias of *Little Mermaid* c513, which is listed under its own id — plus liqueur c053, Acre c081, Bibli c320, and Pin c342, none of which has a model in the current catalog), so cards referencing them fail loudly at build time instead of silently inheriting SSR.
- Launch roster: the [Release dates](#release-dates) section below — the 63 NIKKEs dated 11/04/2022 are exactly the NIKKEs released with the game; that list is used here for the launch roster only.
- Cross-check: <https://nikke.gg/characters/> (client-rendered; its latest-48 roster confirmed the same id scheme).
- Release status: `../nikke-viewer` — `assets/js/json/released_units.js` (the release flag, 262 units; everything it lists is released, though it may lag recent releases) plus the banner tracker and the Release dates list (both incomplete), cross-checked against the International fandom wiki (below).
- Release dates cross-check: <https://nikke-goddess-of-victory-international.fandom.com> — character-page infoboxes carry release dates (verified 2026-10-24): resolved Lily (06/12/2025), Mecha Shifty (04/01/2025), Kurumi (02/12/2026), Avistar (04/23/2026), Aigis (08/13/2026), Claire (09/24/2025), Chime (10/30/2025), Syuen (04/01/2024), Shifty (04/01/2023), Rapunzel (11/04/2022); confirmed no pages for Bibli, liqueur, Acre; *Endless* is a story NPC (deceased), not playable. Model list: the current one is `database/src/utils/json/l2d.json` (740 models — a full client dump including story/boss/NPC/TTS models, so *presence* is not evidence of release); `assets/js/json/l2d.json` (267) is the stale Rust-viewer list, and its 5 extra named models (liqueur, Acre, Bibli, Pin; Siren c340 = the data-mined entry for the released *Little Mermaid* c513, whose in-story nickname is "Siren") plus its raw-id placeholders (c122, c211, c913; c250 renamed *Mass Produced Red*; *Self*/*Choice* on sentinel id c9999) are absent from the current catalog. Absence from the banner tracker or the Release dates list is *not* evidence of release.

## Packs

| # | Pack | Window¹ | New | Re-appears | Base forms | Launch | Collab | Reserve | Total |
|---|------|--------|-----|-----------|------------|--------|--------|---------|-------|
| 1 | **ELYSION** | 2022-11-04 | 0 | 0 | 0 | 19 | 0 | 0 | **19** |
| 2 | **TETRA** | 2022-11-04 | 0 | 0 | 0 | 22 | 0 | 0 | **22** |
| 3 | **MISSILIS** | 2022-11-04 | 0 | 0 | 0 | 22 | 0 | 0 | **22** |
| 4 | **Genesis** | 2022-11-10 – 2023-05-31 | 18 | 0 | 0 | 0 | 1 | 2 | **21** |
| 5 | **Abyss** | 2023-06-14 – 2023-11-22 | 14 | 2 | 1 | 0 | 0 | 3 | **20** |
| 6 | **Molten** | 2023-12-06 – 2024-05-30 | 15 | 3 | 2 | 0 | 0 | 0 | **20** |
| 7 | **Neon Genesis** | 2024-06-06 – 2024-11-21 | 16 | 6 | 3 | 0 | 0 | 0 | **25** |
| 8 | **Red Hood** | 2024-12-05 – 2025-05-29 | 15 | 6 | 2 | 0 | 0 | 0 | **23** |
| 9 | **Tactical** | 2025-06-12 – 2025-08-21 | 8 | 10 | 2 | 0 | 0 | 0 | **20** |
| 10 | **Outbreak** | 2025-09-04 – 2025-11-20 | 8 | 11 | 0 | 0 | 1 | 0 | **20** |
| 11 | **Blizzard** | 2025-12-04 – 2026-05-28 | 14 | 5 | 1 | 0 | 0 | 0 | **20** |
| 12 | **Pumpkin Witch** | 2026-06-11 – 2026-10-08 | 11 | 11 | 5 | 0 | 0 | 0 | **27** |
| — | — | — | **119**³ | 54² | 16 | 63 | 2 | 5 | **259** |

¹ from the first to the last *new* NIKKE released in the pack (banner end-dates overlap between neighbours); the base packs share the game's launch date (2022-11-04), a week before the tracker's first banner (Helm, 2022-11-10).
² roster slots, not distinct NIKKEs — several re-list NIKKEs featured in earlier packs.
³ 119 roster slots + *Alice* (c191), whose first-appearance banner (2023-04-12, pack 4's window) is covered by her launch slot in pack 2 — all 120 banner first appearances stay covered, nothing double-counted.
⁴ collab NIKKES released inside the pack's window with no first-appearance banner in the tracker (so the New table never lists them) — classified as Collab rather than Reserve; drawn from the commons reserve like Reserve picks.

### 1 · ELYSION — 2022-11-04 (19 NIKKEs)

**Launch (19)** — the ELYSION-manufactured NIKKEs released with the game; Rapi — the set's face — leads as 0001 ahead of the SSR block, then SSR → SR → R (ties by NIKKE id):

| NIKKE | ID | Rarity |
|---|---|---|
| Rapi | c010 | SR |
| Signal | c022 | SSR |
| Poli | c030 | SSR |
| Miranda | c032 | SSR |
| Brid | c070 | SSR |
| Soline | c071 | SSR |
| Diesel | c072 | SSR |
| Emma | c090 | SSR |
| Vesti | c091 | SSR |
| Eunhwa | c092 | SSR |
| Privaty | c170 | SSR |
| Guillotine | c180 | SSR |
| Maiden | c181 | SSR |
| Neon | c011 | SR |
| Marian | c013 | SR |
| Delta | c020 | SR |
| Soldier EG | c300 | R |
| Soldier FA | c301 | R |
| Soldier OW | c306 | R |

**Reserve (0)**: *Bibli* (c320) was the candidate top-up but is dropped — a base pack carries launch-day NIKKEs only, so the pack stands at 19; she remains in the commons reserve.

### 2 · TETRA — 2022-11-04 (22 NIKKEs)

**Launch (22)** — the TETRA-manufactured NIKKEs released with the game, SSR → SR → R (ties by NIKKE id); base *Ludmilla* — TETRA per her skin c194, model pending — closes the roster:

| NIKKE | ID | Rarity |
|---|---|---|
| Mary | c130 | SSR |
| Sugar | c140 | SSR |
| Milk | c141 | SSR |
| Frima | c142 | SSR |
| Yulha | c171 | SSR |
| Alice | c191 | SSR |
| Rupee | c200 | SSR |
| Yan | c201 | SSR |
| Dolla | c202 | SSR |
| Exia | c210 | SSR |
| Novel | c212 | SSR |
| Folkwang | c242 | SSR |
| Noise | c430 | SSR |
| Volume | c431 | SSR |
| Aria | c432 | SSR |
| Anis | c012 | SR |
| Belorta | c060 | SR |
| Mica | c061 | SR |
| iDoll Flower | c304 | R |
| iDoll Ocean | c305 | R |
| iDoll Sun | c308 | R |
| Ludmilla † | — | SSR |

*Alice* (c191) is counted here; her first-appearance banner (2023-04-12, pack 4's window) is covered by her launch slot.

† not in the viewer database yet — see build status.

### 3 · MISSILIS — 2022-11-04 (22 NIKKEs)

**Launch (22)** — the 16 MISSILIS-manufactured NIKKEs released with the game (SSR → SR → R, ties by NIKKE id), then the 6 PILGRIM fairy-tale NIKKEs — *Snow White*, *Rapunzel*, *Scarlet*, *Harran*, *Isabel*, *Noah* (all SSR, NIKKE-id order):

| NIKKE | ID | Rarity |
|---|---|---|
| Centi | c080 | SSR |
| Liter | c082 | SSR |
| Drake | c101 | SSR |
| Maxwell | c102 | SSR |
| Crow | c110 | SSR |
| Pepper | c131 | SSR |
| Julia | c150 | SSR |
| Yuni | c160 | SSR |
| Admi | c172 | SSR |
| Epinel | c241 | SSR |
| N102 | c120 | SR |
| Mihara | c161 | SR |
| Ether | c291 | SR |
| Product 08 | c302 | R |
| Product 12 | c303 | R |
| Product 23 | c307 | R |
| Snow White | c220 | SSR |
| Rapunzel | c221 | SSR |
| Scarlet | c222 | SSR |
| Harran | c230 | SSR |
| Isabel | c231 | SSR |
| Noah | c232 | SSR |

### 4 · Genesis — Nov 2022 – May 2023 (21 NIKKEs)

**New (18)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Helm | c352 | 2022-11-10 |
| Laplace | c100 | 2022-11-24 |
| Rupee: Winter Shopper | c203 | 2022-12-08 |
| Anne: Miracle Fairy | c121 | 2022-12-15 |
| Modernia | c260 | 2022-12-31 |
| Jackal | c111 | 2023-01-11 |
| Viper | c112 | 2023-01-11 |
| Cocoa | c311 | 2023-01-31 |
| Soda | c312 | 2023-01-31 |
| Makima | c800 | 2023-02-21 |
| Power | c801 | 2023-02-21 |
| Biscuit | c381 | 2023-03-14 |
| Sakura | c282 | 2023-03-29 |
| D | c040 | 2023-04-12 |
| Dorothy | c233 | 2023-04-26 |
| Blanc | c270 | 2023-05-17 |
| Noir | c271 | 2023-05-24 |
| Rosanna | c280 | 2023-05-31 |

*Alice* (c191) is a launch NIKKE (pack 1) and is counted there; her first-appearance banner (2023-04-12) is covered by her launch slot.

**Re-appears (0)**: —

**Base forms (0)**: — (the pack's former base form, Rupee (c200), is a launch NIKKE and now ships in pack 2)

**Collab (1)**: Himeno (c802 — Chainsaw Man/Devil Hunter collab, released 2023-02-22, the same wave as Makima (c800) and Power (c801) on the New table; no banner in the tracker, so she never landed in it); drawn from the commons reserve.

**Reserve (2)**: Neve (c193 — released 2022-12-08, inside the pack's window), Nihilister (c261 — released 2023-03-30, inside the pack's window); provisional picks from the commons reserve.

### 5 · Abyss — Jun 2023 – Nov 2023 (20 NIKKEs)

**New (14)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Mary: Bay Goddess | c132 | 2023-06-14 |
| Neon: Blue Ocean | c014 | 2023-06-21 |
| Nero | c380 | 2023-07-05 |
| Mast | c350 | 2023-07-19 |
| Anis: Sparkling Summer | c015 | 2023-08-02 |
| Helm: Aquamarine | c353 | 2023-08-09 |
| 2B | c810 | 2023-08-31 |
| A2 | c811 | 2023-09-07 |
| Marchana | c321 | 2023-09-20 |
| Naga | c450 | 2023-10-04 |
| Tia | c451 | 2023-10-11 |
| Quiry | c033 | 2023-10-18 |
| Red Hood | c470 | 2023-11-01 |
| Tove | c192 | 2023-11-22 |

**Re-appears (2)**: Anne: Miracle Fairy (c121), Rupee: Winter Shopper (c203)

**Base forms (1)**: Helm (c352) — the pack's former base forms (Neon, Anis, Mary) are launch NIKKEs, now in packs 1–2

**Reserve (3)**: Snow White: Innocent Days (c224 — released 2023-11-02, inside the pack's window), Siren (c340 — resolved 2026-10-24: *Little Mermaid*'s in-story nickname — "also known as Siren" (the mined c340 entry predates her 2025-04-24 release) — and Little Mermaid is already on the pack 12 roster, so the pick duplicates a roster NIKKE and is **replaced** (recommend: Shifty c907 — ELYSION, R, released 2023-04-01, before the window; Himeno excluded — Chainsaw Man collab, she belongs with Makima and Power in pack 4)), Rei (c392 — released 2023-04-27, the nearest dated release before the window); provisional picks from the commons reserve.

### 6 · Molten — Dec 2023 – May 2024 (20 NIKKEs)

**New (15)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Ludmilla: Winter Owner | c194 | 2023-12-06 |
| Mica: Snow Buddy | c062 | 2023-12-13 |
| Scarlet: Black Shadow | c225 | 2023-12-31 |
| Leona | c382 | 2024-01-11 |
| Moran | c281 | 2024-01-25 |
| Privaty: Unkind Maid | c313 | 2024-02-05 |
| Aid | c310 | 2024-02-15 |
| Elegg | c500 | 2024-02-22 |
| D: Killer Wife | c043 | 2024-03-07 |
| Emilia | c821 | 2024-03-21 |
| Rem | c820 | 2024-03-27 |
| Bay | c550 | 2024-04-11 |
| Crown | c330 | 2024-04-25 |
| Trony | c501 | 2024-05-16 |
| Soda: Twinkling Bunny | c314 | 2024-05-30 |

**Re-appears (3)**: Anne: Miracle Fairy (c121), Rupee: Winter Shopper (c203), Modernia (c260)

**Base forms (2)**: D (c040), Soda (c312) — the pack's former base forms (Mica, Privaty, Scarlet) are launch NIKKEs, now in packs 1–3

### 7 · Neon Genesis — Jun 2024 – Nov 2024 (25 NIKKEs)

**New (16)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Alice: Wonderland Bunny | c195 | 2024-06-06 |
| Clay | c551 | 2024-06-20 |
| Sakura: Bloom in Summer | c284 | 2024-07-04 |
| Rosanna: Chic Ocean | c283 | 2024-07-11 |
| Ein | c391 | 2024-07-25 |
| Zwei | c390 | 2024-08-08 |
| Asuka | c830 | 2024-08-21 |
| Rei Ayanami | c831 | 2024-08-29 |
| Mari | c832 | 2024-09-05 |
| Rouge | c272 | 2024-09-19 |
| Quency: Escape Queen | c403 | 2024-10-03 |
| Phantom | c580 | 2024-10-10 |
| Rumani | c240 | 2024-10-17 |
| Cinderella | c511 | 2024-10-31 |
| Grave | c514 | 2024-11-07 |
| Flora | c411 | 2024-11-21 |

**Re-appears (6)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Mica: Snow Buddy (c062), Mary: Bay Goddess (c132), Ludmilla: Winter Owner (c194), Helm: Aquamarine (c353)

**Base forms (3)**: Rosanna (c280), Sakura (c282), Quency (c402) — the pack's former base form (Alice) is a launch NIKKE, now in pack 2

### 8 · Red Hood — Dec 2024 – May 2025 (23 NIKKEs)

**New (15)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Maiden: Ice Rose | c183 | 2024-12-05 |
| Guillotine: Winter Slayer | c182 | 2024-12-12 |
| Rapi: Red Hood | c016 | 2025-01-01 |
| Mana | c290 | 2025-01-16 |
| Mast: Romantic Maid | c354 | 2025-01-30 |
| Anchor: Innocent Maid | c355 | 2025-02-06 |
| Asuka: WILLE | c835 | 2025-02-20 |
| Rei Ayanami (Tentative Name) | c834 | 2025-02-27 |
| Trina | c412 | 2025-03-13 |
| Bready | c520 | 2025-03-27 |
| Crust | c521 | 2025-04-10 |
| Little Mermaid | c513 | 2025-04-24 |
| Mihara: Bonding Chain | c162 | 2025-05-01 |
| Arcana | c581 | 2025-05-15 |
| Agent K | c041 | 2025-05-29 |

**Re-appears (6)**: Mica: Snow Buddy (c062), Ludmilla: Winter Owner (c194), Scarlet: Black Shadow (c225), Asuka (c830), Rei Ayanami (c831), Mari (c832)

**Base forms (2)**: Mast (c350), Anchor (c351) — the pack's former base forms (Rapi, Mihara, Guillotine, Maiden) are launch NIKKEs, now in packs 1 and 3

### 9 · Tactical — Jun 2025 – Aug 2025 (20 NIKKEs)

**New (8)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| EVE | c850 | 2025-06-12 |
| Raven | c851 | 2025-06-19 |
| Sora | c532 | 2025-07-03 |
| Dorothy: Serendipity | c234 | 2025-07-17 |
| Elegg: Boom and Shock | c502 | 2025-07-24 |
| Emma: Tactical Upgrade | c093 | 2025-08-07 |
| Eunhwa: Tactical Upgrade | c095 | 2025-08-14 |
| Vesti: Tactical Upgrade | c094 | 2025-08-21 |

**Re-appears (10)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Anne: Miracle Fairy (c121), Mary: Bay Goddess (c132), Rupee: Winter Shopper (c203), Rosanna: Chic Ocean (c283), Sakura: Bloom in Summer (c284), Helm: Aquamarine (c353), 2B (c810), A2 (c811)

**Base forms (2)**: Dorothy (c233), Elegg (c500) — the pack's former base forms (Emma, Eunhwa, Vesti) are launch NIKKEs, now in pack 1

### 10 · Outbreak — Sep 2025 – Nov 2025 (20 NIKKEs)

**New (8)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Ade: Agent Bunny | c315 | 2025-09-04 |
| Milk: Blooming Bunny | c143 | 2025-09-11 |
| Ada | c840 | 2025-09-24 |
| Jill | c841 | 2025-10-02 |
| Delta: Ninja Thief | c023 | 2025-10-16 |
| Nayuta | c223 | 2025-10-30 |
| Liberelli | c262 | 2025-11-06 |
| Soline: Frost Ticket | c074 | 2025-11-20 |

**Re-appears (11)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Anne: Miracle Fairy (c121), Mary: Bay Goddess (c132), Guillotine: Winter Slayer (c182), Maiden: Ice Rose (c183), Rupee: Winter Shopper (c203), Dorothy (c233), Modernia (c260), Helm: Aquamarine (c353), Red Hood (c470)

**Base forms (0)**: — (the pack's former base forms — Delta, Soline, Milk — are launch NIKKEs, now in packs 1–2)

**Collab (1)**: Claire (c842 — Resident Evil, matching the pack's RE collab; **released 2025-09-24** — *Claire Redfield* (B.S.T.), the RE collab trio with Ada (c840) and Jill (c841), inside the pack's window (2025-09-04 – 2025-11-20); absent from the banner tracker and Release dates list, both proven incomplete — no banner, so never in the New table); drawn from the commons reserve.

**Reserve (0)**: —

### 11 · Blizzard — Dec 2025 – May 2026 (20 NIKKEs)

**New (14)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Diesel: Winter Sweets | c075 | 2025-12-04 |
| Brid: Silent Track | c073 | 2025-12-10 |
| Snow White: Heavy Arms | c471 | 2025-12-31 |
| Label | c582 | 2026-01-14 |
| Velvet | c316 | 2026-01-29 |
| Chisato | c860 | 2026-02-11 |
| Takina | c861 | 2026-02-18 |
| E.H. | c113 | 2026-03-05 |
| Arcana: Fortune Mate | c583 | 2026-03-19 |
| Snow Crane | c620 | 2026-04-09 |
| Anis: Star | c017 | 2026-04-22 |
| Neon: Vision Eye | c018 | 2026-04-29 |
| Mint | c600 | 2026-05-14 |
| Prika | c601 | 2026-05-28 |

**Re-appears (5)**: Rapi: Red Hood (c016), Guillotine: Winter Slayer (c182), Maiden: Ice Rose (c183), EVE (c850), Raven (c851)

**Base forms (1)**: Arcana (c581) — the pack's former base forms (Neon, Anis, Brid, Diesel, Snow White) are launch NIKKEs, now in packs 1–3

### 12 · Pumpkin Witch — Jun 2026 – Oct 2026 (27 NIKKEs)

**New (11)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Ark Ranger Black | c570 | 2026-06-11 |
| Cinderella: Crystal Wave | c515 | 2026-07-02 |
| Marciana: Marine Study | c322 | 2026-07-08 |
| Laplace: Ultimate Hero | c103 | 2026-07-23 |
| Maxwell: Ordinary Mechanic | c105 | 2026-07-29 |
| Queen (Makoto Nijima) † | c870 | 2026-08-12 |
| Yukiko † | c871 | 2026-08-19 |
| Drake: Great Villain | c104 | 2026-09-03 |
| Guilty: Mighty Bunny | c404 | 2026-09-17 |
| Sin: Swift Bunny | c405 | 2026-09-23 |
| Belorta: Pumpkin Witch | c063 | 2026-10-08 |

**Re-appears (11)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Mica: Snow Buddy (c062), Anne: Miracle Fairy (c121), Guillotine: Winter Slayer (c182), Maiden: Ice Rose (c183), Ludmilla: Winter Owner (c194), Rupee: Winter Shopper (c203), Dorothy: Serendipity (c234), Sakura: Bloom in Summer (c284), Helm: Aquamarine (c353)

**Base forms (5)**: Laplace (c100), Marchana (c321), Guilty (c400), Sin (c401), Cinderella (c511) — the pack's former base forms (Belorta, Drake, Maxwell) are launch NIKKEs, now in pack 3

† not in the viewer database yet — see build status.

## Naming

- Series: **NIKKE REBORN**; the twelve packs are its expansions, shipped as `cards/ELYSION`, `cards/TETRA`, `cards/MISSILIS`, `cards/Genesis`, `cards/Abyss`, `cards/Molten`, `cards/NeonGenesis`, `cards/RedHood`, `cards/Tactical`, `cards/Outbreak`, `cards/Blizzard`, `cards/PumpkinWitch` (matching the existing `cards/Alpha` single-word convention).
- Each pack name is its headline content:

| Pack | Name | Why |
|---|---|---|
| 1 | ELYSION | the ELYSION line of the launch roster — the set's face Rapi (0001), Neon, the maid line, the Soldier trio |
| 2 | TETRA | the TETRA line of the launch roster — SSR headliners (Mary, Sugar, Alice, Aria …) plus the iDoll trio |
| 3 | MISSILIS | the MISSILIS line of the launch roster (Admi, Centi, the Product trio …) plus the 6 PILGRIM fairy-tale NIKKEs |
| 4 | Genesis | the game's launch wave — the first banner NIKKEs after the base packs (Helm, Laplace, …) |
| 5 | Abyss | the ocean-skin summer (Mary: Bay Goddess, Neon: Blue Ocean, Anis: Sparkling Summer, Helm: Aquamarine) |
| 6 | Molten | the v2.0-era window: Scarlet, the first winter limiteds, D: Killer Wife, Emilia/Rem |
| 7 | Neon Genesis | the NERV collab trio (Asuka, Rei Ayanami, Mari) + Ein/Zwei |
| 8 | Red Hood | Rapi: Red Hood's winter, plus the second NERV wave (Asuka: WILLE, Rei Ayanami (TN)) |
| 9 | Tactical | the Emma/Eunhwa/Vesti: Tactical Upgrade wave with EVE, Raven, Sora |
| 10 | Outbreak | the Resident Evil collab (Ada, Jill) and the bunny duo (Ade, Milk) |
| 11 | Blizzard | the Dec 2025–Jan 2026 winter wave (Diesel: Winter Sweets, Brid: Silent Track, Snow White: Heavy Arms) |
| 12 | Pumpkin Witch | Belorta's Halloween banner, the bunny twins (Guilty, Sin) and the Kuroko's collab |

## Build status

- Base packs 1–3: 62 of the 63 launch NIKKEs are in `database/characters.json` — renderable today. Base *Ludmilla* (TETRA, 0022) has no viewer model yet (her skin *Ludmilla: Winter Owner*, c194, ships in pack 6).
- Card numbering is **per pack**: each pack's cards run 0001, 0002, … in roster order, so the pack and the number together identify a card (the viewer NIKKE id in each table row is unrelated). The first 7 drafted cards sit in their base packs — `cards/ELYSION/`: 0001 *Rapi*, 0005 *Brid*; `cards/TETRA/`: 0006 *Alice*, 0015 *Aria*, 0016 *Anis*, 0017 *Belorta*; `cards/MISSILIS/`: 0009 *Admi*. `cards/Genesis/` awaits its launch-wave cards.
- Packs 5–11: every NIKKE is in `database/characters.json` — renderable today.
- Pack 12: needs two viewer models before it can render — *Queen (Makoto Nijima)* (c870) and *Yukiko* (c871) (Kuroko's Basketball collab, Aug 2026). All 28 other NIKKEs in the pack are ready.
- The global-launch standard banners (Ryu, Meryl, Bittercandy …) are absent from both the banner tracker and the viewer database, so those NIKKEs sit outside the 63-renderable launch roster that the base packs now carry; if wanted, that is a 13th "launch" pack pending viewer models.

## Commons reserve

16 NIKKEs from the viewer database are in no pack roster (down from 61: 38 launch NIKKEs moved to the base packs; 7 drawn as pack top-ups — Reserve: Genesis ×2, Abyss ×3; Collab: Genesis ×1, Outbreak ×1). *Endless* (c371) is a story NPC (deceased; Chapter 39: Gene debut) — NPCs are card-able and she stays in the pool. They are the staple fillers for the packs' common slots (and the raw material for a future "Classics" reissue pack). R-ranks have no skill cut-in, so they would carry static + idle only.

| ID | NIKKE | Rarity |
|---|---|---|
| c053 | liqueur ‡ | R |
| c081 | Acre ‡ | R |
| c190 | Lucilla | SSR |
| c226 | Rapunzel: Pure Grace | SSR |
| c320 | Bibli ‡ | SSR |
| c331 | Chime | SSR |
| c342 | Pin ‡ | SSR |
| c361 | Kilo | SSR |
| c371 | Endless | SSR |
| c441 | Avistar | SSR |
| c852 | Lily | SR |
| c862 | Kurumi | SR |
| c872 | Aigis | SR |
| c901 | Syuen | R |
| c907 | Shifty | R |
| c993 | Mecha Shifty | R |

‡ Unreleased — data-mined: no release flag (`released_units.js`), no banner, no Release dates entry, no wiki page. Audited against the viewer's **current** model catalog — `../nikke-viewer`'s `database/src/utils/json/l2d.json` (740 models, a full client dump including story/boss/NPC/TTS models, so *presence* is not evidence of release; the older `assets/js/json/l2d.json` (267) is stale and is not used for release inference) and the International fandom wiki (verified 2026-10-24). 4 of the 16 reserve members are ‡: liqueur (c053), Acre (c081), Bibli (c320), Pin (c342) — no model in the current catalog (present in the stale assets list, since removed), no wiki page; not cardable until a model is restored. *Endless* (c371) is a story NPC (deceased; Chapter 39: Gene debut) — not a playable NIKKE, but NPCs are card-able and she stays in the pool (her SSR is the viewer database's value, not an in-game rarity). The other 11 are released, dated where available: Rapunzel 11/04/2022 (base; Pure Grace skin c226 undated), Shifty 04/01/2023, Syuen 04/01/2024, Kilo 04/25/2024, Mecha Shifty 04/01/2025, Lily 06/12/2025 (Stellar Blade), Chime 10/30/2025, Kurumi 02/12/2026 (Oshi no Ko), Avistar 04/23/2026, Aigis 08/13/2026 (Persona 3), Lucilla (undated — full gameplay entry in the viewer's `Characters.json` but no wiki page). ‡ members count toward the reserve only as filler, and a "Classics" reissue pack would not carry them. Of the seven drawn top-ups, no unreleased pick remains: Claire (c842, drawn for pack 10) is released — *Claire Redfield* (B.S.T.), released 09/24/2025, inside the pack's window (2025-09-04 – 2025-11-20); Siren (c340, drawn for pack 5) is confirmed as *Little Mermaid*'s in-story nickname ("also known as Siren"; the mined c340 entry predates the 04/24/2025 release), and Little Mermaid is already on the pack 12 roster — so that pick duplicates a roster NIKKE and is replaced (recommend: Shifty c907 — before the window; Himeno is reserved for the Genesis pack with the Chainsaw Man trio).

## Data notes

- Packs 4–5 begin with the KR-launch era (Nov 2022 – Mar 2023); the tracker's history is the true release order across servers.
- Spelling quirks from the source data: the database spells c321 *Marchana* (officially Marciana) and c310 *Aid* (officially Ade); the banner titles read *K* (database: Agent K) and *Liberalio* (database: Liberelli). Pack rosters use the database names (the renderable ones); banner names are preserved in `database/banners.json`.
- The launch roster (the base packs' 63 NIKKEs, all 11/04/2022) comes from the Release dates section; the tracker's first banner (Helm, 11/10/2022) postdates the game's launch by a week — the standard launch banners are untracked (see build status).
- The 63 launch NIKKEs split by manufacturer as TETRA 21, ELYSION 19, MISSILIS 16, PILGRIM 6 (plus *Ludmilla*, TETRA, model pending). The base packs keep single-manufacturer rosters: MISSILIS pairs with the 6 PILGRIM fairy-tale NIKKEs (22), and ELYSION stands at 19: its candidate reserve top-up (*Bibli*, c320 — also ELYSION) is dropped because a base pack carries launch-day NIKKEs only (purity beats the 20 lower bound; she is unreleased — data-mined, with no model in the current viewer catalog — and not launch-day), and she remains in the commons reserve.
- *Alice* (c191) is the only NIKKE who is both a launch NIKKE (11/04/2022) and a banner first appearance (2023-04-12, pack 4's window); she is counted once, in the TETRA base pack, and her banner is covered there.
- Base *Ludmilla* is not in the viewer database (only her skin c194, pack 6); the other 62 launch NIKKEs are. *Marian*'s database name carries a leading underscore (`_Marian`, c013); pack rosters use the clean name, as throughout.
- Pack 12's re-appearances: the concurrent re-run window nominally carries 14 NIKKEs; three (Mary: Bay Goddess c132, Rosanna: Chic Ocean c283, Elegg: Boom and Shock c502) are trimmed to keep the roster at 27. Drop the trim if 20–30 is a soft bound (roster 30).
- The Release dates list ends at *Ein* (07/25/2024) and names two NIKKEs outside the renderable roster (*Pascal*, *Ram*); it is used here for the 11/04/2022 launch roster only.
- `cards/Alpha` is the dev prototype (Rapi + Neon, including sub-flavor viewer ids like `c010_02` White Promise and `c016_01` Red Hood Red Flavor that sit outside the top-level database). Its NIKKEs are covered by pack 2 (Neon c011, Rapi c010) and pack 8 (Rapi: Red Hood c016); sub-flavors are a future per-card option, not part of this plan.

## Alternatives considered

- **One 63-NIKKE launch pack** (previous draft): rejected — unbalanced on its own, and 81 with the launch wave; the three base packs keep every pack inside 20–30 (ELYSION stands at 19 — launch-day NIKKEs only).
- **21/21/21 by mixing manufacturers**: would move NIKKEs across manufacturer lines (e.g. 2 MISSILIS into ELYSION); rejected — the single-manufacturer split is the point of the base packs.
- **11 packs**: merge 9 (Tactical) + 10 (Outbreak) — 16 new + 21 re-appear slots (several NIKKEs re-listed from both packs) + 2 base forms = 39, trimmed to 30 by dropping 9 re-appears; the 7 reserve top-ups apply to the 12-pack plan only.
- **13 packs**: split 7 (Neon Genesis) at the NERV collab — Jun–Aug 2024 (8 new + 4 re + 2 base = 14, topped up from the reserve to 20) and Sep–Nov 2024 (the NERV trio, Rouge, Quency: Escape Queen, Phantom, Rumani, Cinderella, Grave, Flora: 8 new + 2 re + 1 base = 11, topped up to 20).

## Release dates

+	Name	Release Date
1	Admi	11/04/2022
2	Alice	11/04/2022
3	Anis	11/04/2022
4	Aria	11/04/2022
5	Belorta	11/04/2022
6	Brid	11/04/2022
7	Centi	11/04/2022
8	Crow	11/04/2022
9	Delta	11/04/2022
10	Diesel	11/04/2022
11	Dolla	11/04/2022
12	Drake	11/04/2022
13	Emma	11/04/2022
14	Epinel	11/04/2022
15	Ether	11/04/2022
16	Eunhwa	11/04/2022
17	Exia	11/04/2022
18	Folkwang	11/04/2022
19	Frima	11/04/2022
20	Guillotine	11/04/2022
21	Harran	11/04/2022
22	iDoll Flower	11/04/2022
23	iDoll Ocean	11/04/2022
24	iDoll Sun	11/04/2022
25	Isabel	11/04/2022
26	Julia	11/04/2022
27	Liter	11/04/2022
28	Ludmilla	11/04/2022
29	Maiden	11/04/2022
30	Marian	11/04/2022
31	Mary	11/04/2022
32	Maxwell	11/04/2022
33	Mica	11/04/2022
34	Mihara	11/04/2022
35	Milk	11/04/2022
36	Miranda	11/04/2022
37	N102	11/04/2022
38	Neon	11/04/2022
39	Noah	11/04/2022
40	Noise	11/04/2022
41	Novel	11/04/2022
42	Pepper	11/04/2022
43	Poli	11/04/2022
44	Privaty	11/04/2022
45	Product 08	11/04/2022
46	Product 12	11/04/2022
47	Product 23	11/04/2022
48	Rapi	11/04/2022
49	Rapunzel	11/04/2022
50	Rupee	11/04/2022
51	Scarlet	11/04/2022
52	Signal	11/04/2022
53	Snow White	11/04/2022
54	Soldier EG	11/04/2022
55	Soldier FA	11/04/2022
56	Soldier OW	11/04/2022
57	Soline	11/04/2022
58	Sugar	11/04/2022
59	Vesti	11/04/2022
60	Volume	11/04/2022
61	Yan	11/04/2022
62	Yulha	11/04/2022
63	Yuni	11/04/2022
64	Helm	11/10/2022
65	Laplace	11/24/2022
66	Neve	12/08/2022
67	Rupee: Winter Shopper	12/08/2022
68	Anne: Miracle Fairy	12/15/2022
69	Modernia	01/01/2023
70	Guilty	01/12/2023
71	Jackal	01/12/2023
72	Quency	01/12/2023
73	Sin	01/12/2023
74	Viper	01/19/2023
75	Cocoa	02/01/2023
76	Soda	02/01/2023
77	Himeno	02/22/2023
78	Makima	02/22/2023
79	Power	02/22/2023
80	Biscuit	03/15/2023
81	Nihilister	03/30/2023
82	Sakura	03/30/2023
83	D	04/13/2023
84	Dorothy	04/27/2023
85	Rei	04/27/2023
86	Blanc	05/18/2023
87	Noir	05/25/2023
88	Rosanna	06/01/2023
89	Nero	06/06/2023
90	Mary: Bay Goddess	06/15/2023
91	Neon: Blue Ocean	06/22/2023
92	Mast	07/20/2023
93	Anchor	08/03/2023
94	Anis: Sparkling Summer	08/03/2023
95	Helm: Aquamarine	08/10/2023
96	2B	09/01/2023
97	Pascal	09/01/2023
98	A2	09/08/2023
99	Marciana	09/21/2023
100	Naga	10/05/2023
101	Tia	10/12/2023
102	Quiry	10/19/2023
103	Red Hood	11/02/2023
104	Snow White: Innocent Days	11/02/2023
105	Tove	11/23/2023
106	Ludmilla: Winter Owner	12/07/2023
107	Mica: Snow Buddy	12/14/2023
108	Scarlet:Black Shadow	01/01/2024
109	Leona	01/11/2024
110	Moran	01/25/2024
111	Privaty: Unkind Maid	02/05/2024
112	Ade	02/15/2024
113	Elegg	02/22/2024
114	D: Killer Wife	03/07/2024
115	Emilia	03/21/2024
116	Ram	03/21/2024
117	Rem	03/28/2024
118	Bay	04/11/2024
119	Crown	04/25/2024
120	Kilo	04/25/2024
121	Trony	05/16/2024
122	Soda: Twinkling Bunny	05/30/2024
123	Alice: Wonderland Bunny	06/06/2024
124	Clay	06/20/2024
125	Sakura: Bloom In Summer	07/04/2024
126	Rosanna: Chic Ocean	07/11/2024
127	Ein	07/25/2024

**The base packs' launch roster:** entries 1–63 (all dated 11/04/2022 — the NIKKEs released with the game) form the three base packs (ELYSION, TETRA, MISSILIS) and release before every other pack; entries 64 onward are post-launch releases already covered by the packs above (the list ends at Ein, 07/25/2024).

## Changelog

- 2026-10-24: the ELYSION base pack stands at 19 — the *Bibli* (c320) reserve top-up is dropped, base packs carry launch-day NIKKEs only (purity beats the 20 lower bound); *Bibli* returns to the commons reserve (16 → 17), reserve top-ups 7 → 6, total roster 259 → 258. Release-status audit via the viewer (`../nikke-viewer`), corrected: the current model catalog is `database/src/utils/json/l2d.json` (740 models, full client dump) — `assets/js/json/l2d.json` (267), used for an interim flip, is stale, and its 5 extra named models (liqueur, Acre, Bibli, Siren, Pin) are absent from the current catalog; that interim "stale flag → released" flip is therefore retracted except for Kilo (dated 04/25/2024 in the Release dates list). The ‡ mark now covers 10 reserve members — 4 with no current model (liqueur, Acre, Bibli, Pin) and 6 with client models but no release trace (Endless, Avistar, Lily, Kurumi, Aigis, Mecha Shifty) — plus both pack picks (Siren c340 → pack 5, Claire c842 → pack 10), keep-or-replace pending; *Bibli* is unreleased (data-mined) after all — the pack 1 exclusion stands on both grounds (unreleased and not launch-day). Siren c340 (pack 5 pick) resolved the same day: it is the data-mined pre-release alias of *Little Mermaid* (c513, released 2025-04-24, pack 12 roster) — the pick duplicates a roster NIKKE, so it is replaced (recommend Himeno c802, the only dated released reserve member before the pack's 2023 window); c340 itself has no model in the current catalog. Claire c842 (pack 10 pick) resolved the same day: likely released — a Resident Evil collab character of the Outbreak period (the trio with Ada c840 and Jill c841); its absence from the banner tracker and Release dates list is source incompleteness, not non-release; the pick stands. The International fandom wiki (verified 2026-10-24) then resolved the rest: all five remaining ‡ reserve members are released with dates (Mecha Shifty 04/01/2025, Lily 06/12/2025, Kurumi 02/12/2026, Avistar 04/23/2026, Aigis 08/13/2026) — the reserve's ‡ set is now just the 4 no-model names (liqueur, Acre, Bibli, Pin, confirmed page-less); *Endless* (c371) is removed from the reserve — a story NPC (deceased), not a playable NIKKE (17 → 16); *Siren* confirmed as *Little Mermaid*'s in-story nickname rather than a pre-release alias. *Endless* (c371) is restored to the reserve (16 → 17) — NPCs are card-able. The five stale `characters.json` entries (Siren c340 and the four no-model ‡ names) are dropped from the file (206 → 201). *Himeno* (c802) is confirmed a Chainsaw Man/Devil Hunter collab NIKKE (wiki: same 02/22/2023 wave as Makima c800 and Power c801) — drawn to the Genesis pack instead of Abyss filler (Reserve 2 → 3; pack 20 → 21; top-ups 6 → 7; total 258 → 259), leaving the commons reserve (17 → 16); the pack 5 replacement recommendation becomes *Shifty* (c907, ELYSION R, 04/01/2023). A `Collab` grouping is added (new summary-table column + per-pack line, footnote ⁴): collab NIKKES released in-window with no banner in the tracker are classified as Collab rather than Reserve — *Himeno* moves from Genesis's Reserve to its Collab line (Genesis 3 → 2 Reserve, 1 Collab) and *Claire* (c842, Resident Evil — the only other ABNORMAL among the drawn top-ups) from Outbreak's Reserve to its Collab line (Outbreak 1 → 0 Reserve, 1 Collab); totals unchanged (Reserve 7 → 5, Collab 2, 259). The commons reserve table is reformatted to one member per row (cosmetic).
- 2026-10-22: launch roster (the 63 base NIKKEs, per the new Release dates section) split into three base packs before all the others — ELYSION (20, the set's face Rapi leading as 0001), TETRA (22, incl. Ludmilla †), MISSILIS (16 MISSILIS + 6 PILGRIM) — grouped by manufacturer (ELYSION first as the face-card line, then by launch-line size), ordered SSR → SR → R (ties by NIKKE id; Rapi leads ELYSION as 0001) instead of alphabetical; the 22 launch NIKKEs previously printed as base forms in the other packs move to the base packs; 7 reserve top-ups (ELYSION ×1, Genesis ×2, Abyss ×3, Outbreak ×1) hold those packs at 20; commons reserve 61 → 16; 12-pack structure with every pack inside 20–30.
- 2025-10-21: plan drafted from the banner history (165 banners) and the 206-skin viewer database; 9-pack structure settled at 20–30 NIKKEs per pack.
