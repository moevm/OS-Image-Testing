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
                this.currentConfig = {
                    suites: [
                        "FILE_SUITE",
                        "MEMORY_SUITE",
                        "SYSCALLS_SUITE",
                        "IPC_SUITE",
                    ],
                    suite_durations: {
                        FILE_SUITE: 300,
                        MEMORY_SUITE: 100,
                        SYSCALLS_SUITE: 200,
                        IPC_SUITE: 100,
                        NETWORK_SUITE: 200,
                    },
                    selected_tests: {},
                };
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
            radio.addEventListener("change", (e) => {
                console.log("Config mode changed to:", e.target.value);
                const panel = document.getElementById("customConfigPanel");
                if (panel) {
                    panel.style.display =
                        e.target.value === "custom" ? "block" : "none";
                    if (e.target.value === "custom" && this.availableSuites) {
                        this.renderConfigUI();
                    }
                }
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

            const div = document.createElement("div");
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
                            Default duration: ${suiteInfo.default_duration}s |
                            Tests: ${suiteInfo.test_count || 0}
                        </div>
                        <div style="margin-top: 10px; ${!isChecked ? "opacity: 0.5;" : ""}">
                            <label style="font-size: 0.9em;">
                                Custom duration (seconds):
                                <input type="number"
                                       id="duration_${suiteName}"
                                       value="${currentDuration}"
                                       min="10"
                                       step="10"
                                       style="width: 100px; margin-left: 10px; padding: 4px;"
                                       ${!isChecked ? "disabled" : ""}>
                            </label>
                            <button class="btn-small"
                                    style="margin-left: 10px;"
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
            .forEach((cb) => {
                cb.addEventListener("change", (e) => {
                    const suiteDiv = e.target.closest("div");
                    const optionsDiv = suiteDiv.querySelector("div:last-child");
                    const durationInput = suiteDiv.querySelector(
                        `input[id^="duration_"]`,
                    );
                    const selectBtn = suiteDiv.querySelector(".btn-small");

                    if (e.target.checked) {
                        suiteDiv.style.backgroundColor = "#f9f9f9";
                        if (optionsDiv) optionsDiv.style.opacity = "1";
                        if (durationInput) durationInput.disabled = false;
                        if (selectBtn) selectBtn.disabled = false;
                    } else {
                        suiteDiv.style.backgroundColor = "#fff";
                        if (optionsDiv) optionsDiv.style.opacity = "0.5";
                        if (durationInput) durationInput.disabled = true;
                        if (selectBtn) selectBtn.disabled = true;
                    }
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

                        const durationInput = document.getElementById(
                            `duration_${suiteName}`,
                        );
                        if (durationInput) {
                            suiteDurations[suiteName] = parseInt(
                                durationInput.value,
                            );
                        }
                    }
                });

            const config = {
                suites: selectedSuites,
                suite_durations: suiteDurations,
                selected_tests: this.currentConfig.selected_tests || {},
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
                };
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
}

let testConfigManager;
document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM loaded, initializing TestConfigManager...");
    testConfigManager = new TestConfigManager();
    window.testConfigManager = testConfigManager;
});
