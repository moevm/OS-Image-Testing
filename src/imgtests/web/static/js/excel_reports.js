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

document.getElementById("exportBtn").addEventListener("click", function () {
    const btn = this;
    btn.disabled = true;
    btn.textContent = "Generating...";

    fetch("/api/export-excel/", {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/json",
        },
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                window.location.href = data.file_url;
                location.reload();
            } else {
                alert("Error: " + data.error);
                btn.disabled = false;
                btn.textContent = "Export to Excel";
            }
        })
        .catch((error) => {
            alert("Error: " + error);
            btn.disabled = false;
            btn.textContent = "Export to Excel";
        });
});
