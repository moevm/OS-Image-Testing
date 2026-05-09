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

const csrfToken = getCookie("csrftoken");

document.getElementById("runTestsBtn").addEventListener("click", function () {
    const btn = this;
    const outputContainer = document.getElementById("outputContainer");

    btn.disabled = true;
    btn.textContent = "Running...";
    outputContainer.textContent = "Tests Running...";

    fetch("/run-tests/", {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json",
        },
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
