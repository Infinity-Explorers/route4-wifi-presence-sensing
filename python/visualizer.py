"""
Signal Analysis and Visualization Module for Route 4 Wi-Fi Presence Sensing.
Authored by Tasneem (Member 3), refactored for modular integration with Member 2 and Member 4.
"""

from __future__ import annotations

from collections import deque
import random
import time
from typing import Optional, Tuple, List

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# ---------------------------------------------------------------------------
# UI Theme & Colors
# ---------------------------------------------------------------------------
BG = "#101827"
CARD = "#1B293B"
TEXT = "#E5EDF5"
MUTED = "#91A4B7"
RSSI_COLOR = "#45D6E8"
BASELINE_COLOR = "#43D9A3"
THRESHOLD_COLOR = "#F5B95C"
ALERT_COLOR = "#FF7185"


class RSSIVisualizer:
    """Real-time Matplotlib visualizer and baseline comparator for RSSI signals."""

    def __init__(
        self,
        calibration_count: int = 20,
        initial_baseline: Optional[float] = None,
        initial_std: Optional[float] = None,
        window_seconds: int = 20,
        max_points: int = 300,
        title: str = "Wi-Fi Signal Monitoring System",
        subtitle: str = "Real-Time RSSI Analysis",
    ):
        self.calibration_count = calibration_count
        self.window_seconds = window_seconds
        self.max_points = max_points

        # Dynamic or predefined baseline
        self.baseline_mean: Optional[float] = initial_baseline
        self.baseline_std: Optional[float] = initial_std
        self.threshold: Optional[float] = (2 * initial_std) if (initial_std is not None) else None
        self.calibration_samples: List[float] = []

        if self.baseline_mean is not None and self.threshold is not None:
            self.upper_threshold = self.baseline_mean + self.threshold
            self.lower_threshold = self.baseline_mean - self.threshold
            self.is_calibrated = True
        else:
            self.upper_threshold = None
            self.lower_threshold = None
            self.is_calibrated = False

        # Ring buffers for time-series display
        self.time_data: deque = deque(maxlen=max_points)
        self.rssi_data: deque = deque(maxlen=max_points)
        self.start_time: float = time.time()
        self.last_status: str = "WAITING"
        self.last_status_color: str = MUTED

        # Build figure and styling
        self._build_figure(title, subtitle)

    def _build_figure(self, title: str, subtitle: str) -> None:
        self.fig, self.ax = plt.subplots(figsize=(11, 7))
        self.fig.patch.set_facecolor(BG)
        self.ax.set_facecolor(CARD)

        self.fig.suptitle(title, fontsize=19, fontweight="bold", color=TEXT, y=0.96)
        self.ax.set_title(subtitle, color=MUTED, pad=15)

        (self.line,) = self.ax.plot(
            [], [], color=RSSI_COLOR, linewidth=2.5, marker="o", markersize=5, label="Live RSSI"
        )

        # Baseline & threshold indicator lines
        self.line_baseline = self.ax.axhline(
            self.baseline_mean if self.baseline_mean is not None else -50,
            color=BASELINE_COLOR,
            linestyle="--",
            linewidth=2,
            label="Baseline",
            visible=(self.is_calibrated),
        )
        self.line_upper = self.ax.axhline(
            self.upper_threshold if self.upper_threshold is not None else -40,
            color=THRESHOLD_COLOR,
            linestyle=":",
            linewidth=1.8,
            label="Upper Threshold",
            visible=(self.is_calibrated),
        )
        self.line_lower = self.ax.axhline(
            self.lower_threshold if self.lower_threshold is not None else -60,
            color=THRESHOLD_COLOR,
            linestyle=":",
            linewidth=1.8,
            label="Lower Threshold",
            visible=(self.is_calibrated),
        )

        # Graph appearance
        self.ax.set_xlabel("Time (seconds)", color=TEXT)
        self.ax.set_ylabel("RSSI (dBm)", color=TEXT)
        self.ax.set_ylim(-90, -30)
        self.ax.set_xlim(0, self.window_seconds)
        self.ax.tick_params(colors=MUTED)
        self.ax.grid(color="#34445A", linestyle="--", alpha=0.6)

        for spine in self.ax.spines.values():
            spine.set_color("#40516A")

        legend = self.ax.legend(loc="lower right", facecolor=CARD, edgecolor="#40516A", fontsize=9)
        for label in legend.get_texts():
            label.set_color(TEXT)

        # Live telemetry information text
        self.rssi_text = self.fig.text(
            0.13, 0.84, "CURRENT RSSI: -- dBm", color=RSSI_COLOR, fontsize=12, fontweight="bold"
        )
        self.status_text = self.fig.text(
            0.62, 0.84, "STATUS: WAITING", color=MUTED, fontsize=12, fontweight="bold"
        )

        b_txt = f"BASELINE: {self.baseline_mean:.2f} dBm" if self.is_calibrated else "BASELINE: CALIBRATING..."
        t_txt = f"THRESHOLD: +/- {self.threshold:.2f} dB" if self.is_calibrated else "THRESHOLD: --"

        self.baseline_text = self.fig.text(0.13, 0.08, b_txt, color=BASELINE_COLOR, fontsize=10)
        self.threshold_text = self.fig.text(0.62, 0.08, t_txt, color=THRESHOLD_COLOR, fontsize=10)

        plt.subplots_adjust(top=0.78, bottom=0.17, left=0.12, right=0.95)

    def set_baseline(self, mean: float, std: float, multiplier: float = 2.0) -> None:
        """Sets the baseline and threshold levels and updates plot lines."""
        self.baseline_mean = round(float(mean), 2)
        self.baseline_std = round(float(std), 2)
        # Ensure threshold is at least 1.5 dBm to prevent false alarms on clean signals
        self.threshold = round(max(multiplier * self.baseline_std, 1.5), 2)
        self.upper_threshold = round(self.baseline_mean + self.threshold, 2)
        self.lower_threshold = round(self.baseline_mean - self.threshold, 2)
        self.is_calibrated = True

        self.line_baseline.set_ydata([self.baseline_mean, self.baseline_mean])
        self.line_baseline.set_visible(True)

        self.line_upper.set_ydata([self.upper_threshold, self.upper_threshold])
        self.line_upper.set_visible(True)

        self.line_lower.set_ydata([self.lower_threshold, self.lower_threshold])
        self.line_lower.set_visible(True)

        self.baseline_text.set_text(f"BASELINE: {self.baseline_mean:.2f} dBm")
        self.threshold_text.set_text(f"THRESHOLD: +/- {self.threshold:.2f} dB")

    def add_reading(self, rssi: float, elapsed_seconds: Optional[float] = None) -> Tuple[str, str]:
        """
        Ingests a new RSSI sample, manages calibration, and evaluates state.
        Returns: (status, status_color)
        """
        if elapsed_seconds is None:
            elapsed_seconds = round(time.time() - self.start_time, 2)

        self.time_data.append(elapsed_seconds)
        self.rssi_data.append(rssi)

        if not self.is_calibrated:
            self.calibration_samples.append(rssi)
            remaining = self.calibration_count - len(self.calibration_samples)
            if remaining <= 0:
                mean = np.mean(self.calibration_samples)
                std = np.std(self.calibration_samples)
                self.set_baseline(mean, std)
                status = "STABLE"
                status_color = BASELINE_COLOR
            else:
                status = f"CALIBRATING ({len(self.calibration_samples)}/{self.calibration_count})"
                status_color = THRESHOLD_COLOR
        else:
            diff = abs(rssi - self.baseline_mean)
            if diff > self.threshold:
                status = "POSSIBLE_CHANGE"
                status_color = ALERT_COLOR
            else:
                status = "STABLE"
                status_color = BASELINE_COLOR

        self.last_status = status
        self.last_status_color = status_color
        return status, status_color

    def update_plot(self) -> Tuple[any, ...]:
        """Refreshes the Matplotlib elements with buffered data."""
        if not self.rssi_data:
            return self.line, self.rssi_text, self.status_text

        current_t = self.time_data[-1]
        current_rssi = self.rssi_data[-1]

        self.line.set_data(list(self.time_data), list(self.rssi_data))
        self.rssi_text.set_text(f"CURRENT RSSI: {current_rssi:.2f} dBm")
        self.status_text.set_text(f"STATUS: {self.last_status}")
        self.status_text.set_color(self.last_status_color)

        # Dynamic scrolling x-axis window
        left_bound = max(0.0, current_t - (self.window_seconds - 1))
        right_bound = max(float(self.window_seconds), current_t + 1)
        self.ax.set_xlim(left_bound, right_bound)

        return self.line, self.rssi_text, self.status_text


def run_simulation(calibration_count: int = 10, interval_ms: int = 1000):
    """
    Standalone simulation matching Member 3's initial deliverable.
    Runs simulated RSSI perturbations and animates the live chart.
    """
    initial_samples = [-55, -57, -56, -54, -58, -56, -55, -57, -54, -56]
    mean_val = float(np.mean(initial_samples))
    std_val = float(np.std(initial_samples))

    visualizer = RSSIVisualizer(
        calibration_count=calibration_count,
        initial_baseline=mean_val,
        initial_std=std_val,
    )

    frame = 0

    def sim_update(_):
        nonlocal frame
        frame += 1
        # Periodic movement spikes every 8 samples
        if frame > 0 and frame % 8 == 0:
            new_rssi = visualizer.baseline_mean + random.choice([-7, 7])
        else:
            new_rssi = visualizer.baseline_mean + random.randint(-2, 2)

        visualizer.add_reading(float(new_rssi), elapsed_seconds=float(frame))
        return visualizer.update_plot()

    ani = FuncAnimation(visualizer.fig, sim_update, interval=interval_ms, cache_frame_data=False)
    plt.show()


if __name__ == "__main__":
    print("[INFO] Launching Route 4 Visualizer in simulation mode...")
    run_simulation()
