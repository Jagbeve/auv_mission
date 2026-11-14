import csv
import math
import matplotlib.pyplot as plt

TARGET_DEPTH = -2.0
RUNS = ["run1.csv", "run2.csv", "run3.csv", "run4.csv", "run5.csv"]

print("run    depth error   heading error   square miss")

for name in RUNS:
    depth_errors = []
    heading_errors = []
    xs = []
    ys = []

    with open(name) as f:
        for row in csv.DictReader(f):
            phase = row["phase"]
            depth = float(row["depth"])
            heading = float(row["heading"])
            target = float(row["target"])

            # Depth: how far from -2 m, once the sub has finished diving
            if phase != "DIVE" and phase != "SURFACE":
                depth_errors.append(abs(depth - TARGET_DEPTH))

            # Heading: how far from the target while driving each side
            if phase == "SIDE":
                error = (target - heading + 540) % 360 - 180
                heading_errors.append(abs(error))
                xs.append(float(row["y"]))      # east
                ys.append(float(row["x"]))      # north

    avg_depth = sum(depth_errors) / len(depth_errors)
    avg_heading = sum(heading_errors) / len(heading_errors)
    # Square: a perfect square ends where it started
    miss = math.sqrt((xs[-1] - xs[0]) ** 2 + (ys[-1] - ys[0]) ** 2)

    print(f"{name}   {avg_depth:.2f} m        {avg_heading:.1f} deg        {miss:.2f} m")
    plt.plot(xs, ys, label=name)

plt.xlabel("East (m)")
plt.ylabel("North (m)")
plt.title("Square path, all runs (seen from above)")
plt.axis("equal")
plt.legend()
plt.savefig("results.png", dpi=150)
print("Saved results.png")
plt.show()

