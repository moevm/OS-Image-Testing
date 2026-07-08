class TestConfigManager {
    constructor() {
        this.availableSuites = null;
        this.currentConfig = null;
        this.init();
    }

    async init() {
        console.log("TestConfigManager initializing...");
        console.log("Distro name:", window.distroName);

        try {
            await this.loadAvailableSuites();
            await this.loadCurrentConfig();
            this.setupEventListeners();
            this.renderConfigUI();
            console.log("TestConfigManager initialized successfully");
        } catch (error) {
            console.error("Failed to initialize TestConfigManager:", error);
            this.showStatus(
                "Failed to load configuration: " + error.message,
                "error",
            );
        }
    }

    async loadAvailableSuites() {
        try {
            console.log("Loading available suites...");
            const response = await fetch("/api/get_available_suites/");
            console.log("Response status:", response.status);

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}: ${response.statusText}`,
                );
            }

            this.availableSuites = await response.json();
            console.log("Loaded suites:", this.availableSuites);
        } catch (error) {
            console.error("Failed to load available suites:", error);
            this.showStatus(
                "Failed to load test suites: " + error.message,
                "error",
            );
            throw error;
        }
    }

    async loadCurrentConfig() {
        try {
            console.log("Loading current config for:", window.distroName);
            const response = await fetch(
                `/api/get_test_config/${window.distroName}/`,
            );

            if (response.ok) {
                this.currentConfig = await response.json();
                console.log("Loaded config:", this.currentConfig);
            } else {
                console.warn("No existing config, using default");
                this.showStatus(
                    "Failed to load tests for " + window.distroName,
                    "error",
                );
            }
        } catch (error) {
            console.error("Failed to load current config:", error);
            throw error;
        }
    }

    setupEventListeners() {
        console.log("Setting up event listeners...");

        const radioButtons = document.querySelectorAll(
            'input[name="configMode"]',
        );
        console.log("Found radio buttons:", radioButtons.length);

        radioButtons.forEach((radio) => {
            radio.addEventListener("change", (event) => {
                console.log("Config mode changed to:", event.target.value);
                const panel = document.getElementById("customConfigPanel");
                if (panel) {
                    panel.style.display =
                        event.target.value === "custom" ? "block" : "none";
                    if (
                        event.target.value === "custom" &&
                        this.availableSuites
                    ) {
                        this.renderConfigUI();
                    }
                }
            });
        });

        document
            .querySelectorAll('input[name="profiledConfigMode"]')
            .forEach((radio) => {
                radio.addEventListener("change", (event) => {
                    const panel =
                        document.getElementById("profiledCustomPanel");
                    if (event.target.value === "custom") {
                        panel.style.display = "block";
                        this.renderProfilesAndDurationsUI();
                        this.renderPatternUI();
                        this.renderSubsystemsUI();
                    } else {
                        panel.style.display = "none";
                    }
                });
            });

        document
            .querySelectorAll('input[name="profiledRunMode"]')
            .forEach((radio) => {
                radio.addEventListener("change", (event) => {
                    const singlePanel =
                        document.getElementById("singleRunPanel");
                    const matrixPanel =
                        document.getElementById("matrixRunPanel");
                    const isSingle = event.target.value === "single";

                    singlePanel.style.display = isSingle ? "block" : "none";
                    matrixPanel.style.display = isSingle ? "none" : "block";
                    this.renderProfilesAndDurationsUI();
                });
            });

        const saveBtn = document.getElementById("saveConfigBtn");
        if (saveBtn) {
            saveBtn.addEventListener("click", () => this.saveConfig());
            console.log("Save button listener added");
        } else {
            console.error("Save button not found!");
        }

        const resetBtn = document.getElementById("resetConfigBtn");
        if (resetBtn) {
            resetBtn.addEventListener("click", () => this.resetConfig());
            console.log("Reset button listener added");
        } else {
            console.error("Reset button not found!");
        }
    }

    renderConfigUI() {
        console.log("Rendering config UI...");

        if (!this.availableSuites) {
            console.error("No available suites data");
            const suitesDiv = document.getElementById("suitesCheckboxes");
            if (suitesDiv) {
                suitesDiv.innerHTML =
                    '<p style="color: red;">Failed to load test suites. Please refresh the page.</p>';
            }
            return;
        }

        const runsInput = document.getElementById("testRunsCount");
        if (runsInput && this.currentConfig) {
            runsInput.value = this.currentConfig.test_runs_count || 1;
        }

        const suitesDiv = document.getElementById("suitesCheckboxes");
        if (!suitesDiv) {
            console.error("suitesCheckboxes element not found!");
            return;
        }

        suitesDiv.innerHTML = "";

        const suiteNames = Object.keys(this.availableSuites).sort();
        console.log("Rendering suites:", suiteNames);

        if (suiteNames.length === 0) {
            suitesDiv.innerHTML = "<p>No test suites available</p>";
            return;
        }

        suiteNames.forEach((suiteName) => {
            const isChecked =
                this.currentConfig.suites?.includes(suiteName) || false;
            const suiteInfo = this.availableSuites[suiteName];
            const currentDuration =
                this.currentConfig.suite_durations?.[suiteName] ||
                suiteInfo.default_duration ||
                300;
            const durationPrefix = `basic_${suiteName}_duration`;

            const div = document.createElement("div");
            div.className = "suite-config-card";
            div.style.margin = "15px 0";
            div.style.padding = "10px";
            div.style.border = "1px solid #e0e0e0";
            div.style.borderRadius = "5px";
            div.style.backgroundColor = isChecked ? "#f9f9f9" : "#fff";

            div.innerHTML = `
                <div style="display: flex; align-items: flex-start; gap: 10px;">
                    <input type="checkbox"
                           value="${suiteName}"
                           data-suite="${suiteName}"
                           data-duration-prefix="${durationPrefix}"
                           ${isChecked ? "checked" : ""}
                           style="margin-top: 3px;">
                    <div style="flex: 1;">
                        <div>
                            <strong style="font-size: 1.1em;">${suiteName}</strong>
                            <span style="color: #666; margin-left: 10px;">
                                ${suiteInfo.description || "No description"}
                            </span>
                        </div>
                        <div style="margin-top: 8px; color: #999; font-size: 0.9em;">
                            Default duration:
                            ${DurationInput.format(suiteInfo.default_duration)} |
                            Tests: ${suiteInfo.test_count || 0}
                        </div>
                        <div class="suite-options"
                             style="margin-top: 10px; ${!isChecked ? "opacity: 0.5;" : ""}">
                            <div style="font-size: 0.9em;">Custom duration:</div>
                            ${DurationInput.render(
                                durationPrefix,
                                currentDuration,
                                !isChecked,
                            )}
                            <button class="btn-small"
                                    style="margin-top: 10px;"
                                    onclick="testConfigManager.showTestsForSuite('${suiteName}')"
                                    ${!isChecked ? "disabled" : ""}>
                                Select Individual Tests
                            </button>
                            ${
                                this.currentConfig.selected_tests?.[suiteName]
                                    ? `<span style="margin-left: 10px; font-size: 0.85em; color: #28a745;">
                                    ✓ ${this.currentConfig.selected_tests[suiteName].length} test(s) selected
                                </span>`
                                    : ""
                            }
                        </div>
                    </div>
                </div>
            `;

            suitesDiv.appendChild(div);
        });

        document
            .querySelectorAll('#suitesCheckboxes input[type="checkbox"]')
            .forEach((checkbox) => {
                checkbox.addEventListener("change", (event) => {
                    const suiteCard = event.target.closest(
                        ".suite-config-card",
                    );
                    const optionsDiv =
                        suiteCard.querySelector(".suite-options");
                    const selectBtn = suiteCard.querySelector(".btn-small");
                    const disabled = !event.target.checked;

                    suiteCard.style.backgroundColor = disabled
                        ? "#fff"
                        : "#f9f9f9";
                    if (optionsDiv) {
                        optionsDiv.style.opacity = disabled ? "0.5" : "1";
                    }
                    if (selectBtn) {
                        selectBtn.disabled = disabled;
                    }
                    DurationInput.setDisabled(
                        event.target.dataset.durationPrefix,
                        disabled,
                    );
                });
            });

        console.log("UI rendered successfully");
    }

    async showTestsForSuite(suiteName) {
        console.log("Showing tests for suite:", suiteName);

        try {
            const response = await fetch(`/api/get_suite_tests/${suiteName}/`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const tests = await response.json();
            console.log(`Loaded ${tests.length} tests for ${suiteName}`);

            const modal = document.createElement("div");
            modal.className = "modal";
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            `;

            const selectedTests =
                this.currentConfig.selected_tests?.[suiteName] || [];

            modal.innerHTML = `
                <div style="background: white; padding: 20px; border-radius: 5px; max-width: 600px; max-height: 80%; overflow: auto;">
                    <h3>Select tests for ${suiteName}</h3>
                    <p><small>Leave all unchecked to run all tests</small></p>
                    <div id="testsList_${suiteName}">
                        ${tests
                            .map(
                                (test) => `
                            <div style="margin: 8px 0;">
                                <label>
                                    <input type="checkbox" value="${test.name}"
                                           ${selectedTests.includes(test.name) ? "checked" : ""}>
                                    ${test.name}
                                </label>
                            </div>
                        `,
                            )
                            .join("")}
                    </div>
                    <div style="margin-top: 20px;">
                        <button id="saveTestsBtn_${suiteName}" class="btn">Save Selection</button>
                        <button id="cancelTestsBtn" class="btn" style="margin-left: 10px;">Cancel</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            document
                .getElementById(`saveTestsBtn_${suiteName}`)
                .addEventListener("click", () => {
                    const selected = Array.from(
                        modal.querySelectorAll(
                            `#testsList_${suiteName} input:checked`,
                        ),
                    ).map((cb) => cb.value);

                    if (!this.currentConfig.selected_tests) {
                        this.currentConfig.selected_tests = {};
                    }

                    if (selected.length > 0) {
                        this.currentConfig.selected_tests[suiteName] = selected;
                        this.showStatus(
                            `Selected ${selected.length} tests for ${suiteName}`,
                            "success",
                        );
                    } else {
                        delete this.currentConfig.selected_tests[suiteName];
                        this.showStatus(
                            `Will run all tests for ${suiteName}`,
                            "success",
                        );
                    }

                    modal.remove();
                    this.renderConfigUI();
                });

            document
                .getElementById("cancelTestsBtn")
                .addEventListener("click", () => {
                    modal.remove();
                });
        } catch (error) {
            console.error("Failed to load tests:", error);
            this.showStatus("Failed to load tests for " + suiteName, "error");
        }
    }

    async saveConfig() {
        console.log("Saving configuration...");

        try {
            const selectedSuites = [];
            const suiteDurations = {};

            document
                .querySelectorAll('#suitesCheckboxes input[type="checkbox"]')
                .forEach((cb) => {
                    if (cb.checked) {
                        const suiteName = cb.value;
                        selectedSuites.push(suiteName);

                        const durationPrefix =
                            cb.dataset.durationPrefix ||
                            `basic_${suiteName}_duration`;
                        suiteDurations[suiteName] = DurationInput.toSeconds(
                            durationPrefix,
                            `${suiteName} duration`,
                        );
                    }
                });
            const testRunsCount = parseInt(
                document.getElementById("testRunsCount")?.value || "1",
                10,
            );

            const config = {
                suites: selectedSuites,
                suite_durations: suiteDurations,
                selected_tests: this.currentConfig.selected_tests || {},
                test_runs_count: testRunsCount,
            };

            console.log("Saving config:", config);

            const response = await fetch(
                `/api/save_test_config/${window.distroName}/`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": window.csrfToken,
                    },
                    body: JSON.stringify(config),
                },
            );

            if (response.ok) {
                this.currentConfig = config;
                this.showStatus("Configuration saved successfully!", "success");
                console.log("Configuration saved");
            } else {
                const error = await response.text();
                throw new Error(`HTTP ${response.status}: ${error}`);
            }
        } catch (error) {
            console.error("Save failed:", error);
            this.showStatus(
                "Error saving configuration: " + error.message,
                "error",
            );
        }
    }

    async resetConfig() {
        console.log("Resetting configuration...");

        try {
            const response = await fetch(
                `/api/reset_test_config/${window.distroName}/`,
                {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": window.csrfToken,
                    },
                },
            );

            if (response.ok) {
                this.currentConfig = {
                    suites: [
                        "FILE_SUITE",
                        "MEMORY_SUITE",
                        "SYSCALLS_SUITE",
                        "IPC_SUITE",
                        "NETWORK_SUITE",
                    ],
                    suite_durations: {
                        FILE_SUITE: 300,
                        MEMORY_SUITE: 100,
                        SYSCALLS_SUITE: 200,
                        IPC_SUITE: 100,
                        NETWORK_SUITE: 200,
                    },
                    selected_tests: {},
                    test_runs_count: 1,
                };
                const runsInput = document.getElementById("testRunsCount");
                if (runsInput) {
                    runsInput.value = 1;
                }
                this.renderConfigUI();
                this.showStatus("Configuration reset to default", "success");
            }
        } catch (error) {
            console.error("Reset failed:", error);
            this.showStatus("Failed to reset configuration", "error");
        }
    }

    showStatus(message, type) {
        console.log("Status:", type, message);
        const statusDiv = document.getElementById("configStatus");
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.style.color = type === "success" ? "green" : "red";
            setTimeout(() => {
                if (statusDiv.textContent === message) {
                    statusDiv.textContent = "";
                }
            }, 3000);
        }
    }

    renderProfilesAndDurationsUI() {
        const profiles = [
            "load",
            "stress",
            "stability",
            "scalability",
            "volume",
            "isolated",
            "spike",
            "diagnostic",
        ];

        const singleProfileContainer = document.getElementById(
            "singleProfileContainer",
        );
        const singleDurationContainer = document.getElementById(
            "singleDurationContainer",
        );
        singleProfileContainer.innerHTML = "";
        singleDurationContainer.innerHTML = "";

        const select = document.createElement("select");
        select.id = "profileSelect";
        profiles.forEach((profile) => {
            const option = document.createElement("option");
            option.value = profile;
            option.textContent =
                profile.charAt(0).toUpperCase() + profile.slice(1);
            select.appendChild(option);
        });
        singleProfileContainer.appendChild(select);
        singleDurationContainer.innerHTML = DurationInput.render(
            "profiled_single_duration",
            120,
        );

        const matrixContainer =
            document.getElementById("profilesCheckboxes");
        matrixContainer.innerHTML = "";
        profiles.forEach((profile) => {
            const durationPrefix = `profiled_${profile}_duration`;
            const div = document.createElement("div");
            div.style.margin = "10px 0";
            div.style.padding = "8px";
            div.style.border = "1px solid #e0e0e0";
            div.style.borderRadius = "5px";
            div.innerHTML = `
                <label>
                    <input
                        type="checkbox"
                        name="profiles"
                        value="${profile}"
                        data-duration-prefix="${durationPrefix}"
                    >
                    <strong>${profile}</strong>
                </label>
                ${DurationInput.render(durationPrefix, 120, true)}
            `;

            const checkbox = div.querySelector(
                'input[type="checkbox"]',
            );
            checkbox.addEventListener("change", (event) => {
                DurationInput.setDisabled(
                    event.target.dataset.durationPrefix,
                    !event.target.checked,
                );
            });
            matrixContainer.appendChild(div);
        });
    }

    renderPatternUI() {
        const container = document.getElementById("patternContainer");
        container.innerHTML = "";
        const select = document.createElement("select");
        select.id = "profiledPatternSelect";
        ["soft","balanced","intense","extreme","spike"].forEach(p => {
            const opt = document.createElement("option");
            opt.value = p;
            opt.textContent = p.charAt(0).toUpperCase() + p.slice(1);
            select.appendChild(opt);
        });
        container.appendChild(select);
    }

    renderSubsystemsUI() {
        const subsystems = ["file","IPC","memory","network","syscalls","system"];
        const container = document.getElementById("subsystemsCheckboxes");
        container.innerHTML = "";
        subsystems.forEach(subsystem => {
            const div = document.createElement("div");
            div.style.margin = "5px 0";
            div.innerHTML = `
                <label>
                    <input type="checkbox" name="subsystems" value="${subsystem}" checked>
                    ${subsystem}
                </label>
            `;
            container.appendChild(div);
        });
    }
}

let testConfigManager;
document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM loaded, initializing TestConfigManager...");
    testConfigManager = new TestConfigManager();
    window.testConfigManager = testConfigManager;
});
