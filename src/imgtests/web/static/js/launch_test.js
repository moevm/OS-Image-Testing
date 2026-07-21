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

    const runner = document.getElementById('configRunner').value;
    const testRunsCountInput = document.getElementById("testRunsCount");
    const testRunsCount = testRunsCountInput
        ? parseInt(testRunsCountInput.value, 10)
        : 1;

    let config = null;
    if (runner === "profiled") {
        const conf_mode = document.querySelector('input[name="profiledConfigMode"]:checked').value;
        if (conf_mode === "custom") {
            const runMode = document.querySelector('input[name="profiledRunMode"]:checked').value;
            config = runMode === "single" ? collectSingleConfig() : collectMatrixConfig();
        }
    }

    btn.disabled = true;
    btn.textContent = gettext("Running...");
    outputContainer.textContent = gettext("Tests Running...");

    fetch("/run-tests/", {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            test_runs_count: testRunsCount,
            runner: runner,
            config: config,
        }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success && data.task_id) {
                outputContainer.textContent = interpolate(
                    gettext("Tests running... (Task ID: %(task_id)s)"),
                    {task_id: data.task_id},
                    true
                );
                pollStatus(data.task_id);
            } else {
                outputContainer.textContent = interpolate(
                    gettext("Error: %(error)s"),
                    {error: data.error || gettext("Failed to start tests")},
                    true
                );
                btn.disabled = false;
                btn.textContent = gettext("Run tests");
            }
        })
        .catch((error) => {
            outputContainer.textContent = interpolate(
                gettext("Error: %(error)s"),
                {error: error},
                true
            );
            btn.disabled = false;
            btn.textContent = gettext("Run tests");
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
                        gettext("Tests running... Please wait.");
                    setTimeout(checkStatus, 2000);
                } else if (data.status === "completed") {
                    outputContainer.textContent =
                        data.output || gettext("Tests completed successfully.");
                    btn.disabled = false;
                    btn.textContent = gettext("Run tests");
                } else if (data.status === "failed") {
                    let errorMsg = data.error || gettext("Test failed");
                    if (data.stderr) {
                        errorMsg += "\n\nError output:\n" + data.stderr;
                    }
                    if (data.output) {
                        errorMsg += "\n\nOutput:\n" + data.output;
                    }
                    outputContainer.textContent = errorMsg;
                    btn.disabled = false;
                    btn.textContent = gettext("Run tests");
                } else {
                    outputContainer.textContent = gettext("Unknown status");
                    btn.disabled = false;
                    btn.textContent = gettext("Run tests");
                }
            })
            .catch((error) => {
                outputContainer.textContent = interpolate(
                    gettext("Error checking status: %(error)s"),
                    {error: error},
                    true
                );
                btn.disabled = false;
                btn.textContent = gettext("Run tests");
            });
    };

    checkStatus();
}
