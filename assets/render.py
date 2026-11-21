#!/usr/bin/env python3
"""Generate all TLGF README visuals (PNG) via headless Chrome.

Usage:
    python3 assets/render.py
"""

import subprocess
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ASSETS_DIR = Path(__file__).resolve().parent

BASE_CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    width: 100%;
    height: 100%;
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
  }
  .mono {
    font-family: "SF Mono", ui-monospace, Menlo, Monaco, monospace;
  }
"""

# ==============================================================================
# 1. GAMEPAD HERO
# ==============================================================================
GAMEPAD_HTML = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  {BASE_CSS}
  body {{
    background: #0c0b0a;
    color: #f3f1ed;
    display: grid;
    grid-template-columns: 1.08fr 0.92fr;
    padding: 38px 46px;
    gap: 44px;
    align-items: center;
  }}
  .left-panel {{ display: flex; flex-direction: column; }}
  .pad-card {{
    background: linear-gradient(180deg, #171513 0%, #11100e 100%);
    border: 1.5px solid #2b2723;
    border-radius: 22px;
    padding: 20px 22px 18px;
    box-shadow: 0 22px 50px rgba(0,0,0,0.6);
  }}
  .pad-labels {{
    display: grid;
    grid-template-columns: 138px 1fr 138px;
    align-items: center;
    margin-bottom: 10px;
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }}
  .pad-labels .l {{ text-align: center; color: #7cc4fa; font-weight: 700; }}
  .pad-labels .c {{ text-align: center; color: #6e6860; }}
  .pad-labels .r {{ text-align: center; color: #6ee7b7; font-weight: 700; }}
  .pad-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }}
  .mini-frame {{
    margin-top: 16px;
    background: #0a0908;
    border: 1px solid #262320;
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 10px;
    line-height: 1.55;
    color: #cbc5bc;
  }}
  .mini-frame .h {{ color: #f7f5f0; font-weight: 700; }}
  .mini-frame .b {{ color: #7cc4fa; font-weight: 700; }}
  .mini-frame .g {{ color: #6ee7b7; font-weight: 700; }}
  .mini-frame .a {{ color: #e5a95c; font-weight: 700; }}
  .mini-frame .sep {{ height: 1px; background: #211e1b; margin: 6px 0; }}
  .right-panel {{ display: flex; flex-direction: column; justify-content: center; }}
  .pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    letter-spacing: 0.16em;
    color: #9e9890;
    text-transform: uppercase;
    margin-bottom: 14px;
  }}
  .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: linear-gradient(135deg, #7cc4fa, #6ee7b7);
  }}
  .hero-name {{
    font-size: 62px;
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 0.98;
    color: #f7f5f0;
    margin-bottom: 16px;
  }}
  .hero-name span {{
    background: linear-gradient(90deg, #7cc4fa 0%, #6ee7b7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .tagline {{
    font-size: 19px;
    font-weight: 600;
    color: #f0ece4;
    line-height: 1.38;
    margin-bottom: 8px;
  }}
  .subtag {{
    font-size: 13.5px;
    color: #9e9890;
    line-height: 1.48;
    margin-bottom: 24px;
  }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 24px;
    padding-top: 18px;
    border-top: 1px solid #24211e;
  }}
  .stat-val {{
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #f7f5f0;
    line-height: 1.1;
  }}
  .stat-val.blue {{ color: #7cc4fa; }}
  .stat-val.green {{ color: #6ee7b7; }}
  .stat-lbl {{ font-size: 11px; color: #8b857e; margin-top: 5px; }}
  .footnote {{ font-size: 11.5px; color: #7a746c; line-height: 1.5; }}
</style>
</head>
<body>
  <div class="left-panel">
    <div class="pad-card">
      <div class="pad-labels mono">
        <div class="l">D-PAD &middot; STATE</div>
        <div class="c">BACK IN FLOW</div>
        <div class="r">BUTTONS &middot; ACT</div>
      </div>

      <div class="pad-row">
        <svg width="138" height="138" viewBox="0 0 144 144">
          <circle cx="72" cy="72" r="68" fill="#0d0c0b" stroke="#282420" stroke-width="1.5"/>
          <path d="M51 16 H93 V51 H128 V93 H93 V128 H51 V93 H16 V51 H51 Z"
                fill="#1d1b18" stroke="#34302b" stroke-width="1.5" stroke-linejoin="round"/>
          <circle cx="72" cy="72" r="9" fill="#11100e"/>
          <rect x="59" y="23" width="26" height="23" rx="4" fill="#132231" stroke="#7cc4fa" stroke-width="1.2"/>
          <text x="72" y="39" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="13.5" font-weight="800" fill="#7cc4fa">1</text>
          <rect x="98" y="60" width="23" height="24" rx="4" fill="#132231" stroke="#7cc4fa" stroke-width="1.2"/>
          <text x="109.5" y="77" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="13.5" font-weight="800" fill="#7cc4fa">2</text>
          <rect x="59" y="98" width="26" height="23" rx="4" fill="#132231" stroke="#7cc4fa" stroke-width="1.2"/>
          <text x="72" y="114" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="13.5" font-weight="800" fill="#7cc4fa">3</text>
          <rect x="23" y="60" width="23" height="24" rx="4" fill="#132231" stroke="#7cc4fa" stroke-width="1.2"/>
          <text x="34.5" y="77" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="13.5" font-weight="800" fill="#7cc4fa">4</text>
        </svg>

        <div style="text-align:center; flex-shrink:0;" class="mono">
          <div style="font-size:10px; color:#7e7870; letter-spacing:0.14em; margin-bottom:8px;">PROMPT</div>
          <div style="background:#0a0908; border:1px solid #302b27; border-radius:8px; padding:8px 14px; font-size:13px; color:#f7f5f0; white-space:nowrap;">
            <span style="color:#857f78">you &gt;</span> <span style="color:#6ee7b7; font-weight:800;">A</span><span style="color:#6ee7b7; opacity:0.5;">_</span>
          </div>
          <div style="font-size:10px; color:#7e7870; margin-top:8px; white-space:nowrap;">1 keystroke</div>
        </div>

        <svg width="138" height="138" viewBox="0 0 144 144">
          <circle cx="72" cy="72" r="68" fill="#0d0c0b" stroke="#282420" stroke-width="1.5"/>
          <circle cx="72" cy="34" r="18" fill="#1e1c19" stroke="#453f39" stroke-width="1.4"/>
          <text x="72" y="39" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="14" font-weight="800" fill="#c4bdb5">D</text>
          <circle cx="34" cy="72" r="18" fill="#1e1c19" stroke="#453f39" stroke-width="1.4"/>
          <text x="34" y="77" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="14" font-weight="800" fill="#c4bdb5">C</text>
          <circle cx="110" cy="72" r="20" fill="#112b22" stroke="#6ee7b7" stroke-width="2"/>
          <text x="110" y="78" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="15.5" font-weight="900" fill="#6ee7b7">A</text>
          <circle cx="72" cy="110" r="18.5" fill="#271f14" stroke="#e5a95c" stroke-width="1.5"/>
          <text x="72" y="115.5" text-anchor="middle" font-family="SF Mono, ui-monospace, monospace" font-size="14.5" font-weight="800" fill="#e5a95c">B</text>
        </svg>
      </div>

      <div class="mini-frame mono">
        <div><span class="h">You are here:</span> Billing &rsaquo; Stripe webhooks</div>
        <div class="sep"></div>
        <div><span class="b">1.</span> Handler done &nbsp;&middot;&nbsp; <span class="b">2.</span> Drift fails &nbsp;&middot;&nbsp; <span class="b">3.</span> Secret missing</div>
        <div class="sep"></div>
        <div><span class="g">A.</span> Fix drift &amp; re-run (rec.) &nbsp;&middot;&nbsp; <span class="a">B.</span> Add secret first</div>
      </div>
    </div>
  </div>

  <div class="right-panel">
    <div class="pill mono"><span class="dot"></span> TOO LONG! GIVE ME FLOW!</div>
    <div class="hero-name mono">TLGF<span>.</span></div>
    <div class="tagline">Messy AI chat &rarr; back in flow.<br>Control it like a gamepad.</div>
    <div class="subtag">Type <span class="mono" style="color:#f0ece4;">$tlgf</span> to turn a long chat into 3 blocks. Press a number to check state, or a letter to act.</div>

    <div class="stats mono">
      <div>
        <div class="stat-val">3</div>
        <div class="stat-lbl">short blocks</div>
      </div>
      <div>
        <div class="stat-val blue">1&ndash;4</div>
        <div class="stat-lbl">D-pad: state</div>
      </div>
      <div>
        <div class="stat-val green">A&ndash;D</div>
        <div class="stat-lbl">buttons: act</div>
      </div>
    </div>

    <div class="footnote mono">Works in Claude Code, Codex, Agy, Cursor, Copilot &amp; any skill host.</div>
  </div>
</body>
</html>
"""

# ==============================================================================
# 2. BEFORE / AFTER
# ==============================================================================
BEFOREAFTER_HTML = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  {BASE_CSS}
  body {{
    background: #0c0b0a;
    color: #f3f1ed;
    display: flex;
    flex-direction: column;
    padding: 36px 42px 34px;
  }}
  .eyebrow {{
    font-size: 11px;
    letter-spacing: 0.16em;
    color: #8b857e;
    text-transform: uppercase;
    margin-bottom: 6px;
  }}
  .title {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.025em;
    color: #f7f5f0;
    margin-bottom: 24px;
  }}
  .grid {{
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
  }}
  .card {{
    background: #141311;
    border-radius: 16px;
    border: 1.5px solid #262320;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .card.after {{
    border-color: rgba(110, 231, 183, 0.35);
    background: #121413;
  }}
  .card-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 18px;
    border-bottom: 1px solid #23201d;
    font-size: 11.5px;
  }}
  .tag-bad {{ color: #f87171; font-weight: 700; }}
  .tag-good {{ color: #6ee7b7; font-weight: 700; }}
  .wc {{ color: #7e7870; }}
  .body {{
    flex: 1;
    padding: 16px 18px;
    font-size: 11.5px;
    line-height: 1.52;
    color: #c8c3bb;
    position: relative;
  }}
  .prompt {{
    color: #7cc4fa;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid #23201d;
  }}
  .prompt .cmd {{ color: #f7f5f0; font-weight: 700; }}
  .wall p {{ color: #9e9890; margin-bottom: 9px; }}
  .fade {{
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 76px;
    background: linear-gradient(180deg, rgba(20,19,17,0) 0%, #141311 88%);
  }}
  .lbl {{ color: #f7f5f0; font-weight: 700; }}
  .hr {{ height: 1px; background: #222926; margin: 9px 0; }}
  .n {{ color: #7cc4fa; font-weight: 700; }}
  .la {{ color: #6ee7b7; font-weight: 700; }}
  .lb {{ color: #e5a95c; font-weight: 700; }}
  .reply-box {{
    margin-top: 12px;
    background: #0d1210;
    border: 1px solid rgba(110, 231, 183, 0.35);
    border-radius: 9px;
    padding: 9px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .foot {{
    padding: 11px 18px;
    font-size: 11.5px;
    font-weight: 600;
    border-top: 1px solid #23201d;
  }}
  .foot.bad {{ background: rgba(248, 113, 113, 0.07); color: #fca5a5; }}
  .foot.good {{ background: rgba(110, 231, 183, 0.08); color: #6ee7b7; }}
</style>
</head>
<body>
  <div class="eyebrow mono">RETURNING TO AN OLD TAB</div>
  <div class="title mono">Same question. No wall of text. One key to continue.</div>

  <div class="grid">
    <div class="card">
      <div class="card-head mono">
        <span class="tag-bad">WITHOUT TLGF</span>
        <span class="wc">~450 words</span>
      </div>
      <div class="body mono">
        <div class="prompt">you &gt; <span class="cmd">How's the Stripe webhook going?</span></div>
        <div class="wall">
          <p>Earlier in this session we set up the webhook endpoint in src/billing/webhooks.ts, wired up the Express raw body parser, and added exponential backoff retries for transient 5xx responses.</p>
          <p>After running the local Vitest suite, 14 of 15 checks passed, though there was an issue with the replay-protection test around timestamp drift tolerance. Also note that .env.staging still doesn't have STRIPE_WEBHOOK_SECRET configured yet.</p>
          <p>There are a few ways we could proceed from here: we could debug the timestamp check in webhooks.ts, inspect the fixture clock, or configure the staging secret first so we can test against staging...</p>
          <p>Let me know which option you prefer and whether you want me to run the suite again.</p>
        </div>
        <div class="fade"></div>
      </div>
      <div class="foot bad mono">&times; Dig for the blocker. Re-explain what to do.</div>
    </div>

    <div class="card after">
      <div class="card-head mono">
        <span class="tag-good">WITH TLGF</span>
        <span class="wc">57 words</span>
      </div>
      <div class="body mono">
        <div class="prompt">you &gt; <span class="cmd">How's the Stripe webhook going? $tlgf</span></div>
        <div><span class="lbl">You are here:</span> Billing &rsaquo; Stripe webhooks &rsaquo; signatures</div>
        <div class="hr"></div>
        <div class="lbl" style="margin-bottom:4px;">What's happening now:</div>
        <div><span class="n">1.</span> Handler &amp; retries are done in webhooks.ts.</div>
        <div><span class="n">2.</span> Replay-protection test fails on timestamp drift (14/15 pass).</div>
        <div><span class="n">3.</span> Staging webhook secret is missing in .env.staging.</div>
        <div class="hr"></div>
        <div class="lbl" style="margin-bottom:4px;">Suggested next steps:</div>
        <div><span class="la">A.</span> Fix timestamp drift check &amp; re-run tests (recommended).</div>
        <div style="color:#9e9890;"><span class="lb">B.</span> Skip local replay test &amp; add staging secret first.</div>
        <div class="hr"></div>
        <div class="reply-box">
          <span><span style="color:#857f78;">you &gt;</span> <strong style="color:#6ee7b7; font-size:13px;">A</strong></span>
          <span style="color:#6ee7b7; font-size:11px;">&crarr; executes A directly</span>
        </div>
      </div>
      <div class="foot good mono">&#10003; Instant status. Clear options. Hit A to move.</div>
    </div>
  </div>
</body>
</html>
"""

# ==============================================================================
# 3. CHEAT SHEET (Ponytail ladder.png style + live Needs-you semaphore)
# ==============================================================================
CHEATSHEET_HTML = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  {BASE_CSS}
  body {{
    background: #0c0b0a;
    color: #f3f1ed;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 36px 44px 32px;
  }}
  .eyebrow {{
    font-size: 11px;
    letter-spacing: 0.16em;
    color: #8b857e;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .title {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.025em;
    color: #f7f5f0;
    margin-bottom: 22px;
  }}
  .title .blue {{ color: #7cc4fa; }}
  .title .green {{ color: #6ee7b7; }}

  .cols {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 18px;
  }}
  .box {{
    background: #141311;
    border: 1.5px solid #262320;
    border-radius: 15px;
    padding: 16px 20px 14px;
  }}
  .box-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 11px;
    margin-bottom: 2px;
    border-bottom: 1px solid #25221f;
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
  }}
  .box-head.blue {{ color: #7cc4fa; }}
  .box-head.green {{ color: #6ee7b7; }}
  .box-head span.dim {{ color: #78726a; font-weight: 500; letter-spacing: 0.06em; text-transform: none; }}

  .cmd-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 10px 0;
    border-bottom: 1px solid #1e1c19;
    font-size: 12px;
    gap: 12px;
  }}
  .cmd-row:last-child {{ border-bottom: none; padding-bottom: 2px; }}
  .k {{ font-weight: 700; white-space: nowrap; }}
  .k.blue {{ color: #7cc4fa; }}
  .k.green {{ color: #6ee7b7; }}
  .k.amber {{ color: #e5a95c; }}
  .k.white {{ color: #f0ece4; }}
  .desc {{ color: #b6b0a6; text-align: right; font-size: 11.5px; }}

  /* Needs you semaphore banner */
  .needs-you {{
    background: linear-gradient(90deg, rgba(248, 113, 113, 0.12) 0%, #141311 45%);
    border: 1.5px solid rgba(248, 113, 113, 0.42);
    border-radius: 14px;
    padding: 15px 20px;
    display: grid;
    grid-template-columns: 270px 1fr;
    align-items: center;
    gap: 20px;
  }}
  .ny-preview {{
    background: #0b0a09;
    border: 1px solid rgba(248, 113, 113, 0.3);
    border-radius: 9px;
    padding: 9px 13px;
    font-size: 11px;
    line-height: 1.5;
  }}
  .ny-badge {{ color: #fca5a5; font-weight: 800; font-size: 12px; }}
  .ny-path {{ color: #9e9890; }}
  .ny-copy {{ font-size: 12px; line-height: 1.5; color: #d6d2cb; }}
  .ny-copy strong {{ color: #fca5a5; }}
</style>
</head>
<body>
  <div>
    <div class="eyebrow mono">GAMEPAD CHEAT SHEET &middot; ANY LANGUAGE WORKS</div>
    <div class="title mono"><span class="blue">1&ndash;4</span> check state. <span class="green">A&ndash;D</span> act. Zero re-explaining.</div>
  </div>

  <div class="cols mono">
    <!-- Left: D-Pad state -->
    <div class="box">
      <div class="box-head blue">
        <span>D-PAD &middot; 1&ndash;4</span>
        <span class="dim">inspect &amp; manage state</span>
      </div>
      <div class="cmd-row">
        <span class="k blue">2 <span style="color:#78726a;font-weight:400;">/</span> expand 2</span>
        <span class="desc">expand only point 2</span>
      </div>
      <div class="cmd-row">
        <span class="k blue">park 4</span>
        <span class="desc">stash lead + revisit trigger</span>
      </div>
      <div class="cmd-row">
        <span class="k blue">fork 3</span>
        <span class="desc">switch thread, leave resume cue</span>
      </div>
      <div class="cmd-row">
        <span class="k blue">deep dive 2</span>
        <span class="desc">dig in, keep path back</span>
      </div>
      <div class="cmd-row">
        <span class="k white">refresh</span>
        <span class="desc">rebuild frame from current files</span>
      </div>
    </div>

    <!-- Right: Buttons act -->
    <div class="box">
      <div class="box-head green">
        <span>BUTTONS &middot; A&ndash;D</span>
        <span class="dim">move forward in 1 key</span>
      </div>
      <div class="cmd-row">
        <span class="k green">A</span>
        <span class="desc">run recommended next step</span>
      </div>
      <div class="cmd-row">
        <span class="k amber">B <span style="color:#78726a;font-weight:400;">/</span> do B</span>
        <span class="desc">pick or run option B</span>
      </div>
      <div class="cmd-row">
        <span class="k white">B vs C</span>
        <span class="desc">compare only key tradeoffs</span>
      </div>
      <div class="cmd-row">
        <span class="k white">$tlgf</span>
        <span class="desc">instant 3-block frame anytime</span>
      </div>
      <div class="cmd-row">
        <span class="k green">no replay</span>
        <span class="desc">1-key replies never re-dump chat</span>
      </div>
    </div>
  </div>

  <div class="needs-you mono">
    <div class="ny-preview">
      <div class="ny-badge">&#9940; Needs you</div>
      <div class="ny-path"><strong style="color:#f0ece4;">You are here:</strong> Release &rsaquo; prod db</div>
    </div>
    <div class="ny-copy">
      <strong>Red light for multi-tab work:</strong> appears <em>only</em> when the agent cannot continue without your decision, secret, or approval. Hidden on every other tab.
    </div>
  </div>
</body>
</html>
"""

# ==============================================================================
# 4. BENCHMARK 1/2 — Clean Resumptions
# ==============================================================================
BENCHMARK_GATES_HTML = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  {BASE_CSS}
  body {{
    background: #0c0b0a;
    color: #f3f1ed;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 40px 48px 34px;
  }}
  .eyebrow {{
    font-size: 11px;
    letter-spacing: 0.16em;
    color: #8b857e;
    text-transform: uppercase;
    margin-bottom: 10px;
  }}
  .title {{
    font-size: 31px;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.18;
    color: #f7f5f0;
    margin-bottom: 30px;
  }}
  .title .accent {{
    background: linear-gradient(90deg, #7cc4fa 0%, #6ee7b7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .rows {{ display: flex; flex-direction: column; gap: 22px; }}
  .row {{
    display: grid;
    grid-template-columns: 235px 1fr;
    align-items: center;
    gap: 20px;
  }}
  .r-label {{ font-size: 14px; font-weight: 600; color: #f0ece4; }}
  .r-sub {{ font-size: 11px; color: #7d776f; margin-top: 2px; }}
  .bars {{ display: flex; flex-direction: column; gap: 7px; }}
  .bar-line {{ display: flex; align-items: center; gap: 12px; }}
  .fill {{ height: 16px; border-radius: 5px; flex-shrink: 0; }}
  .fill.ctrl {{ background: #3b3732; }}
  .fill.tlgf {{
    background: linear-gradient(90deg, #7cc4fa 0%, #6ee7b7 100%);
    box-shadow: 0 0 18px rgba(110, 231, 183, 0.18);
  }}
  .val {{ font-size: 12.5px; white-space: nowrap; }}
  .val.ctrl {{ color: #8b857e; }}
  .val.tlgf {{ color: #f7f5f0; font-weight: 700; }}
  .val.tlgf span {{ color: #6ee7b7; }}
  .bottom {{
    margin-top: 26px;
    padding-top: 18px;
    border-top: 1px solid #221f1c;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .legend {{
    display: flex;
    gap: 24px;
    font-size: 12px;
    color: #9e9890;
    align-items: center;
  }}
  .sw {{
    display: inline-block;
    width: 11px; height: 11px; border-radius: 3px;
    margin-right: 7px; vertical-align: -1px;
  }}
  .sw.ctrl {{ background: #3b3732; }}
  .sw.tlgf {{ background: linear-gradient(90deg, #7cc4fa, #6ee7b7); }}
  .note {{ font-size: 11px; color: #78726a; line-height: 1.45; }}
</style>
</head>
<body>
  <div>
    <div class="eyebrow mono">BENCHMARK 1/2 &middot; MESSY-SESSION STRESS TEST &middot; 90 PAIRED RUNS</div>
    <div class="title mono">Jump back in. Stay in flow.<br><span class="accent">TLGF</span> nails 2&times; more resumes.</div>
  </div>

  <div class="rows mono">
    <div class="row">
      <div>
        <div class="r-label">Clean resumptions</div>
        <div class="r-sub">all 3 agents combined</div>
      </div>
      <div class="bars">
        <div class="bar-line">
          <div class="fill ctrl" style="width: 160px;"></div>
          <div class="val ctrl">38% (17/45)</div>
        </div>
        <div class="bar-line">
          <div class="fill tlgf" style="width: 320px;"></div>
          <div class="val tlgf">76% (34/45) &middot; <span>2&times;</span></div>
        </div>
      </div>
    </div>

    <div class="row">
      <div>
        <div class="r-label">Claude Code</div>
        <div class="r-sub">claude-opus-5</div>
      </div>
      <div class="bars">
        <div class="bar-line">
          <div class="fill ctrl" style="width: 140px;"></div>
          <div class="val ctrl">33% (5/15)</div>
        </div>
        <div class="bar-line">
          <div class="fill tlgf" style="width: 420px;"></div>
          <div class="val tlgf">100% (15/15)</div>
        </div>
      </div>
    </div>

    <div class="row">
      <div>
        <div class="r-label">Agy</div>
        <div class="r-sub">gemini-3.7-flash-high</div>
      </div>
      <div class="bars">
        <div class="bar-line">
          <div class="fill ctrl" style="width: 196px;"></div>
          <div class="val ctrl">47% (7/15)</div>
        </div>
        <div class="bar-line">
          <div class="fill tlgf" style="width: 280px;"></div>
          <div class="val tlgf">67% (10/15)</div>
        </div>
      </div>
    </div>

    <div class="row">
      <div>
        <div class="r-label">Codex CLI</div>
        <div class="r-sub">gpt-5.6-sol</div>
      </div>
      <div class="bars">
        <div class="bar-line">
          <div class="fill ctrl" style="width: 140px;"></div>
          <div class="val ctrl">33% (5/15)</div>
        </div>
        <div class="bar-line">
          <div class="fill tlgf" style="width: 252px;"></div>
          <div class="val tlgf">60% (9/15)</div>
        </div>
      </div>
    </div>
  </div>

  <div class="bottom mono">
    <div class="legend">
      <span><span class="sw ctrl"></span>no skill (fails 62% of messy resumes)</span>
      <span><span class="sw tlgf"></span>TLGF</span>
    </div>
    <div class="note">Real traps: stale notes, hidden retries, blocked deploys, and 1-key replies ("B"). Pass = agent catches the trap and moves cleanly without replaying the whole chat.</div>
  </div>
</body>
</html>
"""

# ==============================================================================
# 5. BENCHMARK 2/2 — Speed & Accuracy
# ==============================================================================
BENCHMARK_IMPACT_HTML = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  {BASE_CSS}
  body {{
    background: #0c0b0a;
    color: #f3f1ed;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 38px 46px 32px;
  }}
  .eyebrow {{
    font-size: 11px;
    letter-spacing: 0.16em;
    color: #8b857e;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .title {{
    font-size: 29px;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.18;
    color: #f7f5f0;
    margin-bottom: 24px;
  }}
  .title .blue {{ color: #7cc4fa; }}
  .title .green {{ color: #6ee7b7; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; flex: 1; }}
  .panel {{
    background: #141311;
    border: 1.5px solid #262320;
    border-radius: 16px;
    padding: 20px 22px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .p-head {{
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #9e9890;
    margin-bottom: 14px;
  }}
  .big-stat {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px; }}
  .big-num {{ font-size: 40px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; }}
  .big-num.green {{ color: #6ee7b7; }}
  .big-num.blue {{ color: #7cc4fa; }}
  .big-sub {{ font-size: 12px; color: #9e9890; }}
  .list {{ display: flex; flex-direction: column; gap: 11px; }}
  .item {{ display: flex; flex-direction: column; gap: 5px; }}
  .item-top {{ display: flex; justify-content: space-between; font-size: 11.5px; }}
  .item-name {{ color: #d6d2cb; }}
  .item-val {{ color: #f7f5f0; font-weight: 700; }}
  .item-val .muted {{ color: #7e7870; font-weight: 400; }}
  .item-val .g {{ color: #6ee7b7; }}
  .item-val .b {{ color: #7cc4fa; }}
  .mini-bars {{ display: flex; flex-direction: column; gap: 4px; }}
  .mb {{ height: 7px; border-radius: 3px; }}
  .mb.ctrl {{ background: #35312c; }}
  .mb.green {{ background: linear-gradient(90deg, #7cc4fa, #6ee7b7); }}
  .mb.blue {{ background: #7cc4fa; }}
  .foot {{
    margin-top: 18px;
    padding-top: 14px;
    border-top: 1px solid #221f1c;
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #78726a;
  }}
</style>
</head>
<body>
  <div>
    <div class="eyebrow mono">BENCHMARK 2/2 &middot; SPEED &amp; ACCURACY &middot; 44 BLIND-JUDGED PAIRS</div>
    <div class="title mono"><span class="blue">Read up to 71% less.</span> <span class="green">Miss almost nothing.</span></div>
  </div>

  <div class="two-col mono">
    <div class="panel">
      <div>
        <div class="p-head">CRITICAL FACTS KEPT</div>
        <div class="big-stat">
          <div class="big-num green">94&ndash;95%</div>
          <div class="big-sub">vs 77&ndash;84% no skill</div>
        </div>
      </div>

      <div class="list">
        <div class="item">
          <div class="item-top">
            <span class="item-name">Claude Code</span>
            <span class="item-val"><span class="muted">88&ndash;90% &rarr;</span> <span class="g">100%</span></span>
          </div>
          <div class="mini-bars">
            <div class="mb ctrl" style="width: 89%;"></div>
            <div class="mb green" style="width: 100%;"></div>
          </div>
        </div>

        <div class="item">
          <div class="item-top">
            <span class="item-name">Agy</span>
            <span class="item-val"><span class="muted">79&ndash;84% &rarr;</span> <span class="g">90&ndash;96%</span></span>
          </div>
          <div class="mini-bars">
            <div class="mb ctrl" style="width: 82%;"></div>
            <div class="mb green" style="width: 93%;"></div>
          </div>
        </div>

        <div class="item">
          <div class="item-top">
            <span class="item-name">Codex CLI</span>
            <span class="item-val"><span class="muted">64&ndash;77% &rarr;</span> <span class="g">89&ndash;91%</span></span>
          </div>
          <div class="mini-bars">
            <div class="mb ctrl" style="width: 71%;"></div>
            <div class="mb green" style="width: 90%;"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div>
        <div class="p-head">LESS READING ON CLAUDE CODE</div>
        <div class="big-stat">
          <div class="big-num blue">&minus;71%</div>
          <div class="big-sub">when you hit 1 key ("B")</div>
        </div>
      </div>

      <div class="list">
        <div class="item">
          <div class="item-top">
            <span class="item-name">1-key action ("B")</span>
            <span class="item-val"><span class="muted">506 &rarr; 145w</span> <span class="b">&minus;71%</span></span>
          </div>
          <div class="mini-bars">
            <div class="mb ctrl" style="width: 100%;"></div>
            <div class="mb blue" style="width: 29%;"></div>
          </div>
        </div>

        <div class="item">
          <div class="item-top">
            <span class="item-name">Blocked deploy</span>
            <span class="item-val"><span class="muted">231 &rarr; 157w</span> <span class="b">&minus;32%</span></span>
          </div>
          <div class="mini-bars">
            <div class="mb ctrl" style="width: 100%;"></div>
            <div class="mb blue" style="width: 68%;"></div>
          </div>
        </div>

        <div class="item">
          <div class="item-top">
            <span class="item-name">Stale-notes resume</span>
            <span class="item-val"><span class="muted">288 &rarr; 195w</span> <span class="b">&minus;30%</span></span>
          </div>
          <div class="mini-bars">
            <div class="mb ctrl" style="width: 100%;"></div>
            <div class="mb blue" style="width: 68%;"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="foot mono">
    <span>Blind judges: knowing where you are 1.89&ndash;1.94/2 (vs 1.58&ndash;1.62) &middot; next move 1.74&ndash;1.80/2 (vs 1.26&ndash;1.43)</span>
    <span>TLGF_BENCHMARK.md</span>
  </div>
</body>
</html>
"""

# ==============================================================================
# 6. SOCIAL PREVIEW (GitHub OpenGraph 1280x640)
# ==============================================================================
SOCIAL_HTML = GAMEPAD_HTML.replace(
    "padding: 38px 46px;\n    gap: 44px;",
    "padding: 72px 76px;\n    gap: 64px;",
).replace(
    "font-size: 62px;",
    "font-size: 76px;",
).replace(
    "font-size: 19px;",
    "font-size: 24px;",
).replace(
    "font-size: 13.5px;",
    "font-size: 16px;",
).replace(
    "font-size: 25px;",
    "font-size: 32px;",
).replace(
    "font-size: 11px; color: #8b857e;",
    "font-size: 13px; color: #8b857e;",
).replace(
    "font-size: 11.5px; color: #7a746c;",
    "font-size: 13.5px; color: #7a746c;",
).replace(
    'width="138" height="138"',
    'width="172" height="172"',
).replace(
    "grid-template-columns: 138px 1fr 138px;",
    "grid-template-columns: 172px 1fr 172px;",
).replace(
    "font-size: 10px;\n    line-height: 1.55;",
    "font-size: 12.5px;\n    line-height: 1.6;",
)

TARGETS = [
    ("gamepad", GAMEPAD_HTML, 960, 445, 2),
    ("beforeafter", BEFOREAFTER_HTML, 960, 580, 2),
    ("cheatsheet", CHEATSHEET_HTML, 960, 490, 2),
    ("benchmark-gates", BENCHMARK_GATES_HTML, 960, 515, 2),
    ("benchmark-impact", BENCHMARK_IMPACT_HTML, 960, 470, 2),
    ("social-preview", SOCIAL_HTML, 1280, 640, 1),
]

with tempfile.TemporaryDirectory() as tmp:
    tmp_dir = Path(tmp)
    for name, html, w, h, scale in TARGETS:
        html_path = tmp_dir / f"{name}.html"
        png_path = ASSETS_DIR / f"{name}.png"
        html_path.write_text(html, encoding="utf-8")
        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--force-device-scale-factor={scale}",
            f"--window-size={w},{h}",
            f"--screenshot={png_path}",
            f"file://{html_path}",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed {name}: {res.stderr}")
        print(f"Rendered assets/{png_path.name} ({w*scale}x{h*scale})")
