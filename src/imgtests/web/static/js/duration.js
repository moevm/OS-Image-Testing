(function () {
    "use strict";

    const units = [
        { key: "days", label: "Days", max: 9999, multiplier: 86400 },
        { key: "hours", label: "Hours", max: 23, multiplier: 3600 },
        { key: "minutes", label: "Minutes", max: 59, multiplier: 60 },
        { key: "seconds", label: "Seconds", max: 59, multiplier: 1 },
    ];

    const maxTotalSeconds = units.reduce(
        (total, unit) => total + unit.max * unit.multiplier,
        0,
    );

    function validatePrefix(prefix) {
        if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(prefix)) {
            throw new Error(`Invalid duration input prefix: ${prefix}`);
        }
    }

    function normalizeTotalSeconds(totalSeconds) {
        const parsed = Number.parseInt(totalSeconds, 10);
        if (!Number.isFinite(parsed) || parsed < 0) {
            return 0;
        }
        return Math.min(parsed, maxTotalSeconds);
    }

    function split(totalSeconds) {
        let remaining = normalizeTotalSeconds(totalSeconds);
        const values = {};

        units.forEach((unit) => {
            values[unit.key] = Math.floor(remaining / unit.multiplier);
            remaining %= unit.multiplier;
        });

        return values;
    }

    function render(prefix, totalSeconds = 0, disabled = false) {
        validatePrefix(prefix);
        const values = split(totalSeconds);
        const disabledAttribute = disabled ? " disabled" : "";

        const inputs = units
            .map(
                (unit) => `
                    <label class="duration-input-field" for="${prefix}_${unit.key}">
                        <span>${unit.label}</span>
                        <input
                            class="duration-component"
                            type="number"
                            id="${prefix}_${unit.key}"
                            value="${values[unit.key]}"
                            min="0"
                            max="${unit.max}"
                            step="1"
                            inputmode="numeric"
                            title="Allowed range: 0-${unit.max}"
                            ${disabledAttribute}
                        >
                    </label>
                `,
            )
            .join("");

        return `
            <div class="duration-input-group" data-duration-prefix="${prefix}">
                ${inputs}
            </div>
        `;
    }

    function getComponent(prefix, unit) {
        const input = document.getElementById(`${prefix}_${unit.key}`);
        if (!input) {
            throw new Error(`Duration field ${unit.label.toLowerCase()} was not found.`);
        }

        const rawValue = input.value.trim();
        const value = rawValue === "" ? 0 : Number(rawValue);
        const isValid = Number.isInteger(value) && value >= 0 && value <= unit.max;

        input.classList.toggle("duration-input-error", !isValid);
        if (!isValid) {
            input.focus();
            throw new Error(`${unit.label} must be an integer from 0 to ${unit.max}.`);
        }

        return value;
    }

    function toSeconds(prefix, fieldLabel = "Duration") {
        validatePrefix(prefix);
        const total = units.reduce(
            (sum, unit) => sum + getComponent(prefix, unit) * unit.multiplier,
            0,
        );

        if (total === 0) {
            document.getElementById(`${prefix}_seconds`)?.focus();
            throw new Error(`${fieldLabel} must be greater than zero.`);
        }

        return total;
    }

    function setDisabled(prefix, disabled) {
        validatePrefix(prefix);
        units.forEach((unit) => {
            const input = document.getElementById(`${prefix}_${unit.key}`);
            if (input) {
                input.disabled = disabled;
            }
        });
    }

    function format(totalSeconds) {
        const values = split(totalSeconds);
        const parts = [];

        if (values.days > 0) parts.push(`${values.days}d`);
        if (values.hours > 0) parts.push(`${values.hours}h`);
        if (values.minutes > 0) parts.push(`${values.minutes}m`);
        if (values.seconds > 0 || parts.length === 0) parts.push(`${values.seconds}s`);

        return parts.join(" ");
    }

    window.DurationInput = Object.freeze({
        MAX_TOTAL_SECONDS: maxTotalSeconds,
        format,
        render,
        setDisabled,
        split,
        toSeconds,
    });
})();
