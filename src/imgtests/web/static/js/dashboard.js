function loadDistributions() {
    fetch("/api/distros/")
        .then((response) => response.json())
        .then((data) => {
            renderDistributions(data.distributions);
        })
        .catch((error) => console.error("Error:", error));
}

function renderDistributions(distributions) {
    const container = document.getElementById("distrosContainer");
    container.innerHTML = "";
    distributions.forEach((distro) => {
        const link = document.createElement("a");
        link.href = `/${distro.id}/`;
        link.className = "platform-link";
        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "×";
        deleteBtn.className = "delete-btn";
        deleteBtn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            removeDistro(distro.id);
        };
        const linkContent = document.createElement("div");
        linkContent.className = "link-content";
        linkContent.innerHTML = `
            <div class="link-text">
                <h2>${escapeHtml(distro.display_name)}</h2>
                <p>${escapeHtml(distro.description)}</p>
            </div>
        `;

        link.appendChild(linkContent);
        link.appendChild(deleteBtn);
        container.appendChild(link);
    });

    const htmlReportsLink = document.createElement("a");
    htmlReportsLink.href = "/reports/";
    htmlReportsLink.className = "platform-link";
    htmlReportsLink.style.textDecoration = "none";
    htmlReportsLink.innerHTML = `
        <div class="link-content" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="link-text">
                <h2 style="color: white">${gettext("View All .html Reports")}</h2>
                <p style="color: rgba(255, 255, 255, 0.9)">${gettext("Browse all generated .html test reports")}</p>
            </div>
        </div>
    `;
    const excelReportsLink = document.createElement("a");
    excelReportsLink.href = "/excel-reports/";
    excelReportsLink.className = "platform-link";
    excelReportsLink.style.textDecoration = "none";
    excelReportsLink.innerHTML = `
        <div class="link-content" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="link-text">
                <h2 style="color: white">${gettext("View All .xls Reports")}</h2>
                <p style="color: rgba(255, 255, 255, 0.9)">${gettext("Browse all exported .xls test reports")}</p>
            </div>
        </div>
    `;

    container.appendChild(htmlReportsLink);
    container.appendChild(excelReportsLink);
}

function addDistro() {
    const name = prompt(gettext("Enter distribution name (e.g., ubuntu):"));
    if (!name) return;
    const displayName = prompt(gettext("Enter display name (e.g., Ubuntu):"));
    if (!displayName) return;
    const description = prompt(
        gettext("Enter description (optional):"),
        interpolate(
            gettext("Run tests for %(display_name)s platform"),
            {display_name: displayName},
            true
        ),
    );
    fetch("/api/distros/add/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
            name: name,
            display_name: displayName,
            description: description,
        }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                loadDistributions();
            } else {
                alert(interpolate(
                    gettext("Error: %(error)s"),
                    {error: data.error},
                    true
                ));
            }
        })
        .catch((error) => console.error("Error:", error));
}

function removeDistro(distroId) {
    if (!confirm(gettext("Are you sure you want to remove this distribution?"))) return;
    fetch(`/api/distros/remove/${distroId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
        },
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                loadDistributions();
            } else {
                alert(interpolate(
                    gettext("Error: %(error)s"),
                    {error: data.error},
                    true
                ));
            }
        })
        .catch((error) => console.error("Error:", error));
}

function resetDistributions() {
    if (
        !confirm(
            gettext("Reset to default distributions? This will remove all custom distributions."),
        )
    )
        return;

    fetch("/api/distros/reset/", {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
        },
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                loadDistributions();
            } else {
                alert(interpolate(
                    gettext("Error: %(error)s"),
                    {error: data.error},
                    true
                ));
            }
        })
        .catch((error) => console.error("Error:", error));
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

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

document.addEventListener("DOMContentLoaded", () => {
    loadDistributions();
    document.getElementById("addDistroBtn").onclick = addDistro;
    document.getElementById("resetDistrosBtn").onclick = resetDistributions;
});
