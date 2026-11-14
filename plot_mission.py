import csv
import matplotlib.pyplot as plt

# ---------- read the log ----------
times = []
depths = []
headings = []
with open("mission_log.csv") as f:
    reader = csv.DictReader(f)          # each row becomes {"time": ..., "depth": ...}
    for row in reader:
        times.append(float(row["time"]))
        depths.append(float(row["depth"]))
        headings.append(float(row["heading"]))

# ---------- draw two graphs, one above the other ----------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

ax1.plot(times, depths)
ax1.set_ylabel("Depth (m)")
ax1.set_title("Depth over time")

ax2.plot(times, headings)
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Heading (deg)")
ax2.set_title("Heading over time")

plt.tight_layout()
plt.savefig("mission_plot.png", dpi=150)   # saved next to your scripts
print("Saved mission_plot.png")
plt.show()                                 # opens a window