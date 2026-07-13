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
    btn.textContent = "Running...";
    outputContainer.textContent = "Tests Running...";

    // flush progress handler the run tests
    fetch("/flush-progress/").then(() => {
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
    }).then((response) => response.json())
        .then((data) => {
            if (data.success && data.task_id) {
                outputContainer.textContent =
                    "Tests running... (Task ID: " + data.task_id + ")";
                pollStatus(data.task_id);
                // add progress display
                document.getElementById("progress-card").style.display = "block";
                // hide suite | profile depending on selected mode
                if (testing_mode === "profiled") {
                    document.getElementById("current-suite-div").style.display = "none";
                    document.getElementById("last-profile-div").style.display = "inline";
                } else {
                    document.getElementById("current-suite-div").style.display = "inline";
                    document.getElementById("last-profile-div").style.display = "none";
                }
            } else {
                outputContainer.textContent =
                    "Error: " + (data.error || "Failed to start tests");
                btn.disabled = false;
                btn.textContent = "Run tests";
                document.getElementById("progress-card").style.display = "none";
            }
        })
        .catch((error) => {
            outputContainer.textContent = "Error: " + error;
            btn.disabled = false;
            btn.textContent = "Run tests";
            document.getElementById("progress-card").style.display = "none";
        });
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
                    document.getElementById("progress-card").style.display = "none";
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
                    document.getElementById("progress-card").style.display = "none";
                } else {
                    outputContainer.textContent = "Unknown status";
                    btn.disabled = false;
                    btn.textContent = "Run tests";
                    document.getElementById("progress-card").style.display = "none";
                }
            })
            .catch((error) => {
                outputContainer.textContent = "Error checking status: " + error;
                btn.disabled = false;
                btn.textContent = "Run tests";
                document.getElementById("progress-card").style.display = "none";
            });
    };

    checkStatus();
}

const PRGORESS_POLLING_INTERVAL = 3000;

function updateDashboard() {
    fetch("/current-progress/", { cache: "no-store" })
        .then(response => {
            if (!response.ok) throw new Error('Ошибка загрузки файла');
            return response.json();
        })
        .then(data => {
            document.getElementById('error-msg').style.display = 'none';

            const totalTests = data.total_test_count || 0;
            const currentTests = data.test_count || 0;
            const testsPercent = totalTests > 0 ? Math.min(Math.round((currentTests / totalTests) * 100), 100) : 0;

            document.getElementById('tests-text').textContent = `${currentTests} / ${totalTests} (${testsPercent}%)`;
            document.getElementById('tests-bar').style.width = `${testsPercent}%`;


            const totalRuns = data.total_run_count || 0;
            const currentRun = data.current_test_run || 0;
            const runsPercent = totalRuns > 0 ? Math.min(Math.round((currentRun / totalRuns) * 100), 100) : 0;

            const runsBar = document.getElementById('runs-bar');
            const runsText = document.getElementById('runs-text');

            runsBar.style.width = `${runsPercent}%`;

            if (currentRun > 0 && currentRun <= totalRuns) {
                runsBar.classList.add('pulse');
                runsText.textContent = `Run ${currentRun} out of ${totalRuns} is in progress (${runsPercent}%)`;
                runsText.style.color = '#3498db';
            } else {
                runsBar.classList.remove('pulse');
                runsText.textContent = `${currentRun} / ${totalRuns} (${runsPercent}%)`;
                runsText.style.color = '#7f8c8d';
            }

            document.getElementById('current-suite').textContent = data.current_suite;
            document.getElementById('current-test').textContent = data.current_test;
            document.getElementById('last-profile').textContent = data.last_profile_done;
        })
        .catch(error => {
            console.error('JSON processing error:', error);
            document.getElementById('error-msg').style.display = 'block';
        });
}

updateDashboard();
let interval = setInterval(updateDashboard, PRGORESS_POLLING_INTERVAL);
