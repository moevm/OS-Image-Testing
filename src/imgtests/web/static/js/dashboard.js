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
        const versionHtml = distro.version
            ? `<span class="version">${escapeHtml(distro.version)}</span>`
            : "";
        const linkContent = document.createElement("div");
        linkContent.className = "link-content";
        linkContent.innerHTML = `
            <div class="link-text">
                <h2>${escapeHtml(distro.display_name)} ${versionHtml}</h2>
                <p>${escapeHtml(distro.description)}</p>
            </div>
        `;

        link.appendChild(linkContent);
        link.appendChild(deleteBtn);
        container.appendChild(link);
    });

    const reportsLink = document.createElement("a");
    reportsLink.href = "/reports/";
    reportsLink.className = "platform-link";
    reportsLink.style.textDecoration = "none";
    reportsLink.innerHTML = `
        <div class="link-content" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="link-text">
                <h2 style="color: white">View All Reports</h2>
                <p style="color: rgba(255, 255, 255, 0.9)">Browse all generated test reports</p>
            </div>
        </div>
    `;
    container.appendChild(reportsLink);
}

function addDistro() {
    const name = prompt("Enter distribution name (e.g., ubuntu):");
    if (!name) return;
    const displayName = prompt("Enter display name (e.g., Ubuntu):");
    if (!displayName) return;
    const version = prompt("Enter version (optional, e.g., 24.04):", "");
    const description = prompt(
        "Enter description (optional):",
        `Run tests for ${displayName} platform`,
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
            version: version,
        }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                loadDistributions();
            } else {
                alert("Error: " + data.error);
            }
        })
        .catch((error) => console.error("Error:", error));
}

function removeDistro(distroId) {
    if (!confirm("Are you sure you want to remove this distribution?")) return;
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
                alert("Error: " + data.error);
            }
        })
        .catch((error) => console.error("Error:", error));
}

function resetDistributions() {
    if (
        !confirm(
            "Reset to default distributions? This will remove all custom distributions.",
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
                alert("Error: " + data.error);
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
