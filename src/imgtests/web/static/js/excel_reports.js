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

function getCheckedValues(selector) {
    return Array.from(document.querySelectorAll(selector))
        .filter((cb) => cb.checked)
        .map((cb) => cb.value);
}

document.getElementById("exportBtn").addEventListener("click", function () {
    const btn = this;
    const tables = getCheckedValues(".table-checkbox");
    const distributions = getCheckedValues(".distro-checkbox");

    if (tables.length === 0) {
        alert("Please select at least one table.");
        return;
    }
    if (distributions.length === 0) {
        alert("Please select at least one distribution.");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Generating...";

    fetch("/api/export-excel/", {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ tables: tables, distributions: distributions }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                window.location.href = data.file_url;
                location.reload();
            } else {
                alert("Error: " + data.error);
                btn.disabled = false;
                btn.textContent = "Generate New Excel Report";
            }
        })
        .catch((error) => {
            alert("Error: " + error);
            btn.disabled = false;
            btn.textContent = "Generate New Excel Report";
        });
});
