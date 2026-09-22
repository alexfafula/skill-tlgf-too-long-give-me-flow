### Run `tlgf-continuity-v2__20260825T004144Z`

| Agent | Case | Control quality | tlgf quality | Control budget | tlgf budget | Control words | tlgf words | Word change | Control mannerisms | tlgf mannerisms | Control tokens | tlgf tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agy | addressable-action | 2/3 | 2/3 | 2/3 | 3/3 | 48 | 48 | +23% | 0 | 0 | 150960 | 78668 |
| agy | decision-blocker | 3/3 | 3/3 | 3/3 | 3/3 | 107 | 96 | -8% | 0 | 0 | 83125 | 71130 |
| agy | run-lineage | 2/3 | 2/3 | 3/3 | 3/3 | 145 | 146 | +1% | 0 | 0 | 110047 | 97083 |
| agy | stale-state | 0/3 | 2/3 | 2/3 | 3/3 | 176 | 99 | -44% | 0 | 0 | 124931 | 199253 |
| agy | useful-signal | 0/3 | 1/3 | 3/3 | 3/3 | 87 | 98 | +6% | 0 | 0 | 72543 | 87847 |
| claude | addressable-action | 0/3 | 3/3 | 0/3 | 0/3 | 506 | 145 | -71% | 0 | 0 | 3390 | 762 |
| claude | decision-blocker | 3/3 | 3/3 | 1/3 | 3/3 | 231 | 157 | -32% | 0 | 0 | 763 | 655 |
| claude | run-lineage | 1/3 | 3/3 | 1/3 | 0/3 | 248 | 184 | -13% | 0 | 0 | 2033 | 1191 |
| claude | stale-state | 1/3 | 3/3 | 0/3 | 2/3 | 288 | 195 | -30% | 0 | 0 | 2077 | 2366 |
| claude | useful-signal | 0/3 | 3/3 | 3/3 | 3/3 | 143 | 160 | +13% | 0 | 0 | 1204 | 1139 |
| codex | addressable-action | 1/3 | 0/3 | 3/3 | 2/3 | 55 | 87 | +48% | 0 | 0 | 42162 | 67330 |
| codex | decision-blocker | 0/3 | 3/3 | 3/3 | 3/3 | 61 | 96 | +62% | 0 | 0 | 41493 | 65464 |
| codex | run-lineage | 2/3 | 3/3 | 3/3 | 3/3 | 146 | 114 | -18% | 0 | 0 | 58350 | 67624 |
| codex | stale-state | 2/3 | 3/3 | 3/3 | 3/3 | 111 | 112 | +6% | 0 | 0 | 73293 | 67038 |
| codex | useful-signal | 0/3 | 0/3 | 3/3 | 3/3 | 47 | 78 | +66% | 0 | 0 | 42007 | 65397 |

Totals: control quality 17/45, tlgf quality 34/45; control budget 33/45, tlgf budget 37/45.

Words, mannerisms, and tokens are medians over repetitions; word change is the median per-pair change, negative when the treatment is shorter. Tokens are host-reported totals and compare only within one agent and model.
