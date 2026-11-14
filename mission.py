from pymavlink import mavutil
import time, csv

# ---------- settings ----------
TARGET_DEPTH = -2.0   # m (negative = underwater)
SIDE_TIME = 5         # seconds driving each side
FORWARD = 1600        # forward speed (1500 = stop, 1900 = max)
TURN_TOLERANCE = 3    # degrees: "close enough" to the target heading

m = mavutil.mavlink_connection('tcp:127.0.0.1:5762')
m.wait_heartbeat()
print("Connected")

# ---------- helpers ----------
# Switch flight mode (e.g. "ALT_HOLD")
def set_mode(name):
    m.set_mode(m.mode_mapping()[name])
    print("Mode:", name)

# Move the joystick sticks. 1500 = centered/stop for each one.
def send_rc(throttle=1500, yaw=1500, forward=1500):
    ch = [65535] * 18     # don't mess with this
    ch[2] = throttle      # channel 3: up/down
    ch[3] = yaw           # channel 4: turn
    ch[4] = forward       # channel 5: forward/back
    m.mav.rc_channels_override_send(m.target_system, m.target_component, *ch)

# Ask the sub to send a message type hz times per second
def request(msg_id, hz):
    m.mav.command_long_send(m.target_system, m.target_component,
                            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                            msg_id, 1000000 / hz, 0, 0, 0, 0, 0)

request(mavutil.mavlink.MAVLINK_MSG_ID_LOCAL_POSITION_NED, 10)

# The sub's latest depth, heading and position. update() keeps it fresh.
state = {"depth": 0.0, "heading": 0, "x": 0.0, "y": 0.0, "target": 0}
# Read the newest depth, heading and position from the sub
def update():
    while True:
        msg = m.recv_match(type=["VFR_HUD", "LOCAL_POSITION_NED"], blocking=False)
        if msg is None:
            break
        if msg.get_type() == "VFR_HUD":
            state["depth"] = msg.alt
            state["heading"] = msg.heading
        else:                       # position: meters from where the sim started
            state["x"] = msg.x      # north
            state["y"] = msg.y      # east

# Open the CSV log file and write the column names
logfile = open("mission_log.csv", "w", newline="")
log = csv.writer(logfile)
log.writerow(["time", "phase", "depth", "heading", "target", "x", "y"])
start = time.time()
# One tick of the mission: send sticks, read sensors, log a row, wait 0.1 s
def step(phase, **rc):
    send_rc(**rc)
    update()
    log.writerow([round(time.time() - start, 2), phase, state["depth"], state["heading"],
                  state["target"], state["x"], state["y"]])
    time.sleep(0.1)

# How many degrees left to turn to face the target (+ = right, - = left)
def heading_error(target):
    return (target - state["heading"] + 540) % 360 - 180

# Pick a turn stick value: far off = turn hard, close = turn gently
def yaw_toward(target):
    yaw = 1500 + 3 * heading_error(target)
    return int(max(1300, min(1700, yaw)))    # keep between 1300 and 1700

# ---------- mission ----------
try:
    m.arducopter_arm(); m.motors_armed_wait(); print("Armed")
    set_mode("ALT_HOLD")

    # ===== STAGE 1: DIVE =====
    print("DIVE")
    while state["depth"] > TARGET_DEPTH:   # keep diving until 2 m down
        step("DIVE", throttle=1350)

    print("HOLD")
    t = time.time()
    while time.time() - t < 5:       # hold depth for 5 s
        step("HOLD")

    # ===== STAGE 2: SQUARE =====
    start_heading = state["heading"]                            # which way we face now
    targets = []                                     # the 4 headings, one per side
    for i in range(4):                               # i = 0, 1, 2, 3
        heading = (start_heading + 90 * i) % 360     # 90 deg more each side, wrapped to 0-359
        targets.append(heading)
    print("Square headings:", targets)

    for target in targets:
        state["target"] = target         # log which heading we're aiming for
        # --- turn until facing the target (within 3 degrees) ---
        print("TURN to", target)
        while abs(heading_error(target)) > TURN_TOLERANCE:
            step("TURN", yaw=yaw_toward(target))

        # --- drive forward 5 s, still steering so the side stays straight ---
        print("SIDE")
        t = time.time()
        while time.time() - t < SIDE_TIME:
            step("SIDE", forward=FORWARD, yaw=yaw_toward(target))

    # ===== STAGE 3: SURFACE =====
    print("SURFACE")
    while state["depth"] < -0.2:
        step("SURFACE", throttle=1650)

finally:                         # runs no matter what: success, error, or Ctrl+C
    send_rc()                    # center all controls
    m.arducopter_disarm()        # thrusters off
    logfile.close()              # save the CSV
    print("Done. Log saved to mission_log.csv")
