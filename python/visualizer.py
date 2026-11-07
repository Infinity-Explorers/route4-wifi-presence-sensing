import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import random
from collections import deque

# Colors
BG = "#101827"
CARD = "#1B293B"
TEXT = "#E5EDF5"
MUTED = "#91A4B7"
RSSI_COLOR = "#45D6E8"
BASELINE_COLOR = "#43D9A3"
THRESHOLD_COLOR = "#F5B95C"
ALERT_COLOR = "#FF7185"

# Baseline calibration
baseline_samples = [-55, -57, -56, -54, -58,
                    -56, -55, -57, -54, -56]

baseline_mean = np.mean(baseline_samples)
baseline_std = np.std(baseline_samples)
threshold = 2 * baseline_std

upper_threshold = baseline_mean + threshold
lower_threshold = baseline_mean - threshold

print("Baseline:", round(baseline_mean, 2), "dBm")
print("Threshold:", round(threshold, 2), "dB")

# Store the latest readings
time_data = deque(maxlen=30)
rssi_data = deque(maxlen=30)

# Create the graph
fig, ax = plt.subplots(figsize=(11, 7))
fig.patch.set_facecolor(BG)
ax.set_facecolor(CARD)

fig.suptitle(
    "Wi-Fi Signal Monitoring System",
    fontsize=19, fontweight="bold", color=TEXT, y=0.96
)
ax.set_title("Real-Time RSSI Analysis", color=MUTED, pad=15)

line, = ax.plot(
    [], [], color=RSSI_COLOR, linewidth=2.5,
    marker="o", markersize=5, label="Live RSSI"
)

# Baseline and thresholds
ax.axhline(baseline_mean, color=BASELINE_COLOR,
           linestyle="--", linewidth=2, label="Baseline")
ax.axhline(upper_threshold, color=THRESHOLD_COLOR,
           linestyle=":", linewidth=1.8, label="Upper Threshold")
ax.axhline(lower_threshold, color=THRESHOLD_COLOR,
           linestyle=":", linewidth=1.8, label="Lower Threshold")

# Graph appearance
ax.set_xlabel("Time (seconds)", color=TEXT)
ax.set_ylabel("RSSI (dBm)", color=TEXT)
ax.set_ylim(-90, -30)
ax.set_xlim(0, 20)
ax.tick_params(colors=MUTED)
ax.grid(color="#34445A", linestyle="--", alpha=0.6)

for spine in ax.spines.values():
    spine.set_color("#40516A")

legend = ax.legend(
    loc="lower right", facecolor=CARD,
    edgecolor="#40516A", fontsize=9
)
for label in legend.get_texts():
    label.set_color(TEXT)

# Live information
rssi_text = fig.text(
    0.13, 0.84, "CURRENT RSSI: -- dBm",
    color=RSSI_COLOR, fontsize=12, fontweight="bold"
)
status_text = fig.text(
    0.62, 0.84, "STATUS: WAITING",
    color=MUTED, fontsize=12, fontweight="bold"
)
fig.text(
    0.13, 0.08, f"BASELINE: {baseline_mean:.2f} dBm",
    color=BASELINE_COLOR, fontsize=10
)
fig.text(
    0.62, 0.08, f"THRESHOLD: +/- {threshold:.2f} dB",
    color=THRESHOLD_COLOR, fontsize=10
)

# Update the graph every second
def update(frame):

    # Simulated RSSI readings
    if frame > 0 and frame % 8 == 0:
        new_rssi = baseline_mean + random.choice([-7, 7])
    else:
        new_rssi = baseline_mean + random.randint(-2, 2)

    new_rssi = round(new_rssi, 2)

    time_data.append(frame)
    rssi_data.append(new_rssi)

    # Compare the reading with the baseline
    difference = new_rssi - baseline_mean

    if abs(difference) > threshold:
        status = "POSSIBLE_CHANGE"
        status_color = ALERT_COLOR
    else:
        status = "STABLE"
        status_color = BASELINE_COLOR

    # Update the display
    line.set_data(list(time_data), list(rssi_data))
    rssi_text.set_text(f"CURRENT RSSI: {new_rssi:.2f} dBm")
    status_text.set_text(f"STATUS: {status}")
    status_text.set_color(status_color)

    # Keep the latest 20 seconds visible
    ax.set_xlim(max(0, frame - 19), max(20, frame))

    return line, rssi_text, status_text


ani = FuncAnimation(
    fig, update, interval=1000, cache_frame_data=False
)

plt.subplots_adjust(
    top=0.78, bottom=0.17, left=0.12, right=0.95
)
plt.show()