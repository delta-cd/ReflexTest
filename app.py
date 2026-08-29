import random
import time
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client
from user_agents import parse

st.set_page_config(page_title="ReflexDelta // Latency Engine", layout="centered")

# --- Environment & Supabase Setup ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "secret123")
except Exception:
    st.error("SECURITY ERROR: Secrets missing from configuration.")
    st.stop()


@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


supabase: Client = init_supabase()

st.markdown(
    """
    <style>
    .stApp { background-color: #0B0F17; color: #FFFFFF; font-family: monospace; }
    div[data-testid="stNotification"] { background-color: #1F2937 !important; border: 1px solid #374151; }
    iframe { border: none !important; width: 100% !important; height: 380px !important; }
    footer { visibility: hidden !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- User Session Management ---
if "user_uuid" not in st.session_state:
    st.session_state.user_uuid = (
        f"user_{random.randint(100000, 999999)}_{int(time.time())}"
    )

# --- Fetch Global Stats for Percentile Calculation ---
total_players = 0
if supabase:
    try:
        count_res = (
            supabase.table("global_leaderboard")
            .select("*", count="exact")
            .execute()
        )
        total_players = count_res.count if count_res.count else 0
    except Exception:
        total_players = 0

# --- Device Classification ---
try:
    user_agent_string = st.context.headers.get("User-Agent", "")
except AttributeError:
    user_agent_string = ""

user_agent = parse(user_agent_string)
if user_agent.is_mobile:
    detected_device = "Handheld Mobile Device"
elif user_agent.is_tablet:
    detected_device = "Tablet Device"
else:
    detected_device = "Desktop PC / Laptop"

# --- ADMIN ANALYTICS GATEWAY ---
with st.expander("🔒 Admin Analytics Gateway"):
    admin_input = st.text_input(
        "Enter passcode to unlock telemetry database:", type="password"
    )

    if admin_input == ADMIN_PASSWORD:
        st.success("AUTHENTICATED: Telemetry Loaded")
        if supabase:
            try:
                response = (
                    supabase.table("global_leaderboard").select("*").execute()
                )
                data = response.data

                if data and len(data) > 0:
                    df = pd.DataFrame(data)

                    df["reaction_time_ms"] = pd.to_numeric(
                        df["reaction_time_ms"], errors="coerce"
                    )
                    df = df.dropna(subset=["reaction_time_ms"])

                    if not df.empty:
                        scores_array = df["reaction_time_ms"].to_numpy()

                        total_tries = len(df)
                        unique_users = (
                            df["user_session_id"].nunique()
                            if "user_session_id" in df.columns
                            else total_tries
                        )

                        mobile_count = (
                            len(
                                df[
                                    df["device_platform"]
                                    == "Handheld Mobile Device"
                                ]
                            )
                            if "device_platform" in df.columns
                            else 0
                        )
                        pc_count = (
                            len(
                                df[
                                    df["device_platform"]
                                    == "Desktop PC / Laptop"
                                ]
                            )
                            if "device_platform" in df.columns
                            else 0
                        )

                        mean_latency = np.mean(scores_array)
                        median_latency = np.median(scores_array)
                        best_score = np.min(scores_array)
                        std_dev = (
                            np.std(scores_array, ddof=1)
                            if total_tries > 1
                            else 0.0
                        )

                        st.markdown("### 📊 High-Level Metrics")
                        m_col1, m_col2, m_col3 = st.columns(3)
                        with m_col1:
                            st.metric("Total Tries Run", f"{total_tries}")
                            st.metric("Unique Users", f"{unique_users}")
                        with m_col2:
                            st.metric("Mean Latency", f"{mean_latency:.1f} ms")
                            st.metric(
                                "Median Velocity", f"{median_latency:.1f} ms"
                            )
                        with m_col3:
                            st.metric("Best Score", f"{best_score:.1f} ms")
                            st.metric("Std Deviation", f"{std_dev:.1f} ms")

                        st.markdown("---")
                        st.markdown("### 🧬 Mobile vs PC Platform Comparison")

                        p_col1, p_col2 = st.columns(2)
                        with p_col1:
                            st.metric("📱 Mobile Submissions", f"{mobile_count}")
                        with p_col2:
                            st.metric("💻 Desktop PC/Laptop", f"{pc_count}")

                        if "device_platform" in df.columns:
                            breakdown = (
                                df.groupby("device_platform")
                                .agg(
                                    Total_Tries=("reaction_time_ms", "count"),
                                    Unique_Users=("user_session_id", "nunique"),
                                    Mean_Score_ms=("reaction_time_ms", "mean"),
                                    Best_Score_ms=("reaction_time_ms", "min"),
                                )
                                .rename(
                                    columns={
                                        "Total_Tries": "Total Tries",
                                        "Unique_Users": "Unique Users",
                                        "Mean_Score_ms": "Mean Latency (ms)",
                                        "Best_Score_ms": "Best Score (ms)",
                                    }
                                )
                            )
                            st.dataframe(breakdown, use_container_width=True)
                    else:
                        st.info("No valid score rows found in table.")
                else:
                    st.info("Leaderboard currently contains 0 entries.")
            except Exception as e:
                st.error(f"Analysis engine exception: {str(e)}")
        else:
            st.error("Supabase connection offline.")
    elif admin_input != "":
        st.error("ACCESS DENIED: Passcode invalid.")

st.title("ReflexDelta // Latency Engine")
st.write(
    "Sub-millisecond hardware click engine with real-time global ranking."
)
st.markdown("---")

# --- HTML/JS ENGINE WITH CLIENT-SIDE RANK CALCULATOR ---
html_code = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{
    -webkit-tap-highlight-color: transparent;
    user-select: none;
    -webkit-user-select: none;
  }}
  body {{ margin: 0; font-family: monospace; background: transparent; }}
  #target {{
    width: 100%;
    height: 180px;
    border-radius: 12px;
    border: none;
    font-size: 24px;
    font-weight: bold;
    color: white;
    cursor: pointer;
    background-color: #1F2937;
    transition: none !important;
  }}
  .waiting {{ background-color: #1F2937 !important; }}
  .countdown {{ background-color: #D97706 !important; }}
  .ready {{ background-color: #059669 !important; }}
  .early {{ background-color: #DC2626 !important; }}
  #result-box {{
    margin-top: 15px;
    padding: 14px;
    background-color: #111827;
    border-radius: 8px;
    border: 1px solid #374151;
  }}
  .score-title {{ font-size: 20px; color: #10B981; font-weight: bold; }}
  .pb-title {{ font-size: 15px; color: #F59E0B; font-weight: bold; margin-top: 4px; }}
  .stats-details {{ font-size: 13px; color: #9CA3AF; margin-top: 6px; }}
  .rank-highlight {{ color: #60A5FA; font-weight: bold; }}
</style>
</head>
<body>

<button id="target" class="waiting">🎯 INITIALIZE REACTION LOOP<br><br><span style="font-size:14px; font-weight:normal;">(Press inside boundary region to start)</span></button>

<div id="result-box">
  <div id="score-display" class="score-title">Waiting for attempt...</div>
  <div id="pb-display" class="pb-title">⭐ Personal Best: Loading...</div>
  <div id="stats-display" class="stats-details">Total Global Tries Recorded: {total_players}</div>
</div>

<script>
  const button = document.getElementById("target");
  const scoreDisplay = document.getElementById("score-display");
  const pbDisplay = document.getElementById("pb-display");
  const statsDisplay = document.getElementById("stats-display");
  
  let state = "WAITING";
  let startTime = 0;
  let timerId = null;

  function loadPB() {{
    const savedPB = localStorage.getItem("reflex_pb");
    if (savedPB) {{
      pbDisplay.innerHTML = "⭐ Personal Best: " + parseFloat(savedPB).toFixed(1) + " ms";
    }} else {{
      pbDisplay.innerHTML = "⭐ Personal Best: None recorded yet";
    }}
  }}

  function checkAndUpdatePB(newScore) {{
    const savedPB = localStorage.getItem("reflex_pb");
    if (!savedPB || newScore < parseFloat(savedPB)) {{
      localStorage.setItem("reflex_pb", newScore);
      pbDisplay.innerHTML = "⭐ Personal Best: " + newScore.toFixed(1) + " ms (NEW HIGH SCORE!)";
    }} else {{
      pbDisplay.innerHTML = "⭐ Personal Best: " + parseFloat(savedPB).toFixed(1) + " ms";
    }}
  }}

  async function fetchRankAndSaveScore(scoreMs) {{
    statsDisplay.innerHTML = "⏳ Syncing score & calculating global position...";
    
    // 1. Post score directly to Supabase
    try {{
      await fetch("{SUPABASE_URL}/rest/v1/global_leaderboard", {{
        method: "POST",
        headers: {{
          "apikey": "{SUPABASE_KEY}",
          "Authorization": "Bearer {SUPABASE_KEY}",
          "Content-Type": "application/json",
          "Prefer": "return=minimal"
        }},
        body: JSON.stringify({{
          reaction_time_ms: scoreMs,
          device_platform: "{detected_device}",
          user_session_id: "{st.session_state.user_uuid}"
        }})
      }});
    }} catch (e) {{ console.error(e); }}

    // 2. Fetch live rank & percentile dynamically
    try {{
      const rankRes = await fetch("{SUPABASE_URL}/rest/v1/global_leaderboard?select=reaction_time_ms&reaction_time_ms=lte." + scoreMs, {{
        headers: {{
          "apikey": "{SUPABASE_KEY}",
          "Authorization": "Bearer {SUPABASE_KEY}",
          "Range-Unit": "items",
          "Prefer": "count=exact"
        }}
      }});
      
      const totalRes = await fetch("{SUPABASE_URL}/rest/v1/global_leaderboard?select=reaction_time_ms", {{
        headers: {{
          "apikey": "{SUPABASE_KEY}",
          "Authorization": "Bearer {SUPABASE_KEY}",
          "Range-Unit": "items",
          "Prefer": "count=exact"
        }}
      }});

      const contentRangeRank = rankRes.headers.get("content-range");
      const contentRangeTotal = totalRes.headers.get("content-range");

      const rank = contentRangeRank ? parseInt(contentRangeRank.split("/")[1]) : 1;
      const total = contentRangeTotal ? parseInt(contentRangeTotal.split("/")[1]) : 1;
      const percentile = ((rank / total) * 100).toFixed(1);

      statsDisplay.innerHTML = "🏅 Global Position: <span class='rank-highlight'>#" + rank + "</span> of " + total + " total tries (Top <span class='rank-highlight'>" + percentile + "%</span>)";
    }} catch (err) {{
      statsDisplay.innerHTML = "✅ Score saved to database!";
    }}
  }}

  loadPB();

  function handleInput(e) {{
    if (e) e.preventDefault();

    if (state === "WAITING" || state === "EARLY") {{
      state = "COUNTDOWN";
      button.className = "countdown";
      button.innerHTML = "🔴 HOLD FOCUS...<br><br>WAIT FOR SIGNAL";
      
      const delay = Math.random() * 2300 + 1600;
      timerId = setTimeout(() => {{
        state = "READY";
        startTime = performance.now();
        button.className = "ready";
        button.innerHTML = "🟢 SIGNAL ACTIVE<br><br>CLICK NOW!";
      }}, delay);

    }} else if (state === "COUNTDOWN") {{
      clearTimeout(timerId);
      state = "EARLY";
      button.className = "early";
      button.innerHTML = "⚠️ TIMING ERROR<br><br>Anticipation fault. Press to retry.";

    }} else if (state === "READY") {{
      const latency = performance.now() - startTime;
      state = "WAITING";
      button.className = "waiting";
      button.innerHTML = "🎯 INITIALIZE REACTION LOOP<br><br><span style='font-size:14px; font-weight:normal;'>(Press to run again)</span>";
      
      const rounded = parseFloat(latency.toFixed(1));
      
      scoreDisplay.innerHTML = "⏱️ Latency Result: " + rounded.toFixed(1) + " ms";
      checkAndUpdatePB(rounded);
      fetchRankAndSaveScore(rounded);
    }}
  }}

  button.addEventListener("touchstart", handleInput, {{ passive: false }});
  button.addEventListener("mousedown", (e) => {{
    if (e.detail > 0) handleInput(e);
  }});
</script>
</body>
</html>
"""

components.html(html_code, height=380)

st.write("**DATABASE STATUS: ONLINE**")