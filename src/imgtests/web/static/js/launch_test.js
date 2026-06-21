function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1),
                );
                break;
            }
        }
    }
    return cookieValue;
}

function getSelectedSubsystems() {
    return Array.from(document.querySelectorAll('#subsystemsCheckboxes input[type="checkbox"]:checked'))
                .map(cb => cb.value);
}

function collectSingleConfig() {
    return {
        durations: { duration_sec: parseInt(document.getElementById("duration_sec").value, 10) },
        profile: document.getElementById("profileSelect").value,
        pattern: document.getElementById("profiledPatternSelect").value,
        subsystems: getSelectedSubsystems(),
        run_matrix: false
    };
}

function collectMatrixConfig() {
    const durations = {};
    const matrixProfiles = [];

    document.querySelectorAll('#profilesCheckboxes input[type="checkbox"]').forEach(cb => {
        if (cb.checked) {
            matrixProfiles.push(cb.value);
            const durInput = document.getElementById(`duration_${cb.value}`);
            if (durInput) {
                durations[`duration_${cb.value}`] = parseInt(durInput.value, 10);
            }
        }
    });

    return {
        durations: durations,
        matrix_profiles: matrixProfiles,
        pattern: document.getElementById("profiledPatternSelect").value,
        subsystems: getSelectedSubsystems(),
        run_matrix: true
    };
}

const csrfToken = getCookie("csrftoken");

document.getElementById("runTestsBtn").addEventListener("click", function () {
    const btn = this;
    const outputContainer = document.getElementById("outputContainer");

    const testing_mode = document.getElementById('configTestingMode').value;
    const testRunsCountInput = document.getElementById("testRunsCount");
    const testRunsCount = testRunsCountInput
        ? parseInt(testRunsCountInput.value, 10)
        : 1;

    let config = null;
    if (testing_mode === "profiled") {
        const conf_mode = document.getElementById("profiledCustomPanel");
        if (conf_mode === "custom") {
            const runMode = document.querySelector('input[name="profiledRunMode"]:checked').value;
            config = runMode === "single" ? collectSingleConfig() : collectMatrixConfig();
        }
    }

    btn.disabled = true;
    btn.textContent = "Running...";
    outputContainer.textContent = "Tests Running...";

    fetch("/run-tests/", {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            test_runs_count: testRunsCount,
            TESTING_MODE: testing_mode,
            config: config,
        }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success && data.task_id) {
                outputContainer.textContent =
                    "Tests running... (Task ID: " + data.task_id + ")";
                pollStatus(data.task_id);
            } else {
                outputContainer.textContent =
                    "Error: " + (data.error || "Failed to start tests");
                btn.disabled = false;
                btn.textContent = "Run tests";
            }
        })
        .catch((error) => {
            outputContainer.textContent = "Error: " + error;
            btn.disabled = false;
            btn.textContent = "Run tests";
        });
});

function pollStatus(taskId) {
    const btn = document.getElementById("runTestsBtn");
    const outputContainer = document.getElementById("outputContainer");

    const checkStatus = () => {
        fetch("/test-status/" + taskId + "/")
            .then((response) => response.json())
            .then((data) => {
                if (data.status === "running") {
                    outputContainer.textContent =
                        "Tests running... Please wait.";
                    setTimeout(checkStatus, 2000);
                } else if (data.status === "completed") {
                    outputContainer.textContent =
                        data.output || "Tests completed successfully.";
                    btn.disabled = false;
                    btn.textContent = "Run tests";
                } else if (data.status === "failed") {
                    let errorMsg = data.error || "Test failed";
                    if (data.stderr) {
                        errorMsg += "\n\nError output:\n" + data.stderr;
                    }
                    if (data.output) {
                        errorMsg += "\n\nOutput:\n" + data.output;
                    }
                    outputContainer.textContent = errorMsg;
                    btn.disabled = false;
                    btn.textContent = "Run tests";
                } else {
                    outputContainer.textContent = "Unknown status";
                    btn.disabled = false;
                    btn.textContent = "Run tests";
                }
            })
            .catch((error) => {
                outputContainer.textContent = "Error checking status: " + error;
                btn.disabled = false;
                btn.textContent = "Run tests";
            });
    };

    checkStatus();
}
