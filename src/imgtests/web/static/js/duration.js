(function () {
    "use strict";

    const units = [
        {
            key: "days",
            getLabel: () => gettext("Days"),
            max: 9999,
            multiplier: 86400,
        },
        {
            key: "hours",
            getLabel: () => gettext("Hours"),
            max: 23,
            multiplier: 3600,
        },
        {
            key: "minutes",
            getLabel: () => gettext("Minutes"),
            max: 59,
            multiplier: 60,
        },
        {
            key: "seconds",
            getLabel: () => gettext("Seconds"),
            max: 59,
            multiplier: 1,
        },
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
                        <span>${unit.getLabel()}</span>
                        <input
                            class="duration-component"
                            type="number"
                            id="${prefix}_${unit.key}"
                            value="${values[unit.key]}"
                            min="0"
                            max="${unit.max}"
                            step="1"
                            inputmode="numeric"
                            title="${interpolate(
                                gettext("Allowed range: 0-%(max)s"),
                                {max: unit.max},
                                true,
                            )}"
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
            throw new Error(
                interpolate(
                    gettext("Duration field %(field)s was not found."),
                    {field: unit.getLabel().toLowerCase()},
                    true,
                ),
            );
        }

        const rawValue = input.value.trim();
        const value = rawValue === "" ? 0 : Number(rawValue);
        const isValid = Number.isInteger(value) && value >= 0 && value <= unit.max;

        input.classList.toggle("duration-input-error", !isValid);
        if (!isValid) {
            input.focus();
            throw new Error(
                interpolate(
                    gettext("%(field)s must be an integer from 0 to %(max)s."),
                    {field: unit.getLabel(), max: unit.max},
                    true,
                ),
            );
        }

        return value;
    }

    function toSeconds(prefix, fieldLabel) {
        validatePrefix(prefix);
        const label = fieldLabel || gettext("Duration");
        const total = units.reduce(
            (sum, unit) => sum + getComponent(prefix, unit) * unit.multiplier,
            0,
        );

        if (total === 0) {
            document.getElementById(`${prefix}_seconds`)?.focus();
            throw new Error(
                interpolate(
                    gettext("%(field)s must be greater than zero."),
                    {field: label},
                    true,
                ),
            );
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

        if (values.days > 0)
            parts.push(values.days + pgettext("duration unit", "d"));
        if (values.hours > 0)
            parts.push(values.hours + pgettext("duration unit", "h"));
        if (values.minutes > 0)
            parts.push(values.minutes + pgettext("duration unit", "m"));
        if (values.seconds > 0 || parts.length === 0)
            parts.push(values.seconds + pgettext("duration unit", "s"));

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
