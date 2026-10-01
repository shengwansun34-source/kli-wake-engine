import os, json, math, random, time
from fastapi import FastAPI

app = FastAPI()

# ================= 配置区 =================
# 如果你想用 HF 存状态，把下面 REPO_ID 改成你的；如果不用，留空即可
HF_TOKEN = os.environ.get("HF_TOKEN", "")
REPO_ID = ""   # 例如 "你的用户名/kli-wake-state"，不用就留空
STATE_FILE = "activation_state.json"

# 按 PDF 基线参数，λθ 改成 0.25 实现约 4 小时唤醒一次
LAMBDA_0 = 0.25
BETA_D, BETA_T, BETA_X = 1.8, 1.6, 1.2
MU_D, MU_T, MU_X = 0.50, 0.50, 0.00
TAU_D, TAU_T, TAU_X = 12*60, 6*3600, 25*60
SIGMA_T, SIGMA_X = 0.10, 0.18
K_RUN = 0.10
D_MIN, D_MAX = 0.20, 0.80
T_MIN, T_MAX = 0.25, 0.75
X_MIN, X_MAX = -0.40, 0.40
LAM_MIN, LAM_MAX = 0.15, 8.0

# ================= 持久化 =================
def load_state():
    if not REPO_ID:
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            return None
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(REPO_ID, STATE_FILE, token=HF_TOKEN)
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None

def save_state(state):
    if not REPO_ID:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
        return
    try:
        from huggingface_hub import HfApi
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
        HfApi(token=HF_TOKEN).upload_file(
            path_or_fileobj=STATE_FILE,
            path_in_repo=STATE_FILE,
            repo_id=REPO_ID,
            repo_type="dataset",
        )
    except Exception as e:
        print("save_state error:", e)

# ================= 状态初始化 =================
def init_state():
    return {
        "D": 0.50, "T": 0.50, "X": 0.00,
        "theta": -math.log(random.random()),
        "H": 0.0,
        "last_update": time.time(),
        "generation": 0,
    }

# ================= 核心公式 =================
def compute_lambda(state):
    D, T, X = state["D"], state["T"], state["X"]
    exponent = BETA_D*(D-MU_D) + BETA_T*(T-MU_T) + BETA_X*X
    lam = LAMBDA_0 * math.exp(exponent) * 1.0
    return max(LAM_MIN, min(LAM_MAX, lam))

def update_state(state, dt):
    rho_D = 2 ** (-dt / TAU_D) if TAU_D > 0 else 0
    rho_T = 2 ** (-dt / TAU_T) if TAU_T > 0 else 0
    rho_X = 2 ** (-dt / TAU_X) if TAU_X > 0 else 0

    state["D"] = MU_D + (state["D"] - MU_D) * rho_D
    state["D"] = max(D_MIN, min(D_MAX, state["D"]))

    noise_T = random.gauss(0, 1) * math.sqrt(max(0, 1 - rho_T**2))
    state["T"] = MU_T + (state["T"] - MU_T)*rho_T + SIGMA_T * noise_T
    state["T"] = max(T_MIN, min(T_MAX, state["T"]))

    noise_X = random.gauss(0, 1) * math.sqrt(max(0, 1 - rho_X**2))
    state["X"] = state["X"]*rho_X + SIGMA_X * noise_X
    state["X"] = max(X_MIN, min(X_MAX, state["X"]))

    state["last_update"] = time.time()

# ================= 端点 =================
@app.get("/wake")
def wake_check():
    state = load_state() or init_state()
    dt = time.time() - state["last_update"]
    if dt > 0:
        update_state(state, dt)

    lam = compute_lambda(state)
    state["H"] += lam * dt / 3600.0

    if state["H"] >= state["theta"]:
        state["H"] = 0.0
        state["theta"] = -math.log(random.random())
        state["generation"] += 1
        save_state(state)
        return {"wake": True, "activationId": f"wk_{state['generation']}"}

    save_state(state)
    return {
        "wake": False,
        "lambda": round(lam, 4),
        "H": round(state["H"], 4),
        "theta": round(state["theta"], 4),
    }

@app.get("/")
def root():
    return {"status": "ok", "service": "kli-wake-engine"}
