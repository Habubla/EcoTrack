const clockEl = document.getElementById("clock");

function updateClock() {
    if (!clockEl) {
        return;
    }

    const now = new Date();
    const dateText = now.toLocaleDateString(undefined, {
        weekday: "short",
        day: "2-digit",
        month: "short",
        year: "numeric"
    });

    const timeText = now.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit"
    });

    clockEl.textContent = `${dateText} | ${timeText}`;
}

function applyConsumptionBars() {
    const bars = document.querySelectorAll(".consumption-bar");
    bars.forEach((bar) => {
        const width = Number(bar.dataset.width || 0);
        const safeWidth = Math.max(0, Math.min(100, width));
        bar.style.width = `${safeWidth}%`;
    });
}

updateClock();
setInterval(updateClock, 60000);
applyConsumptionBars();
