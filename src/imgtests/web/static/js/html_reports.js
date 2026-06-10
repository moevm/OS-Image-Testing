const select1 = document.getElementById("exp-select-1");
const select2 = document.getElementById("exp-select-2");
const genBtn = document.getElementById("generate-btn");
const resultDiv = document.getElementById("compare-result");

function fillSelect(select, data) {
    data.forEach((exp) => {
        const opt = document.createElement("option");
        opt.value = exp.id;
        opt.textContent = `#${exp.id} | ${exp.os} | ${exp.description || "(no description)"} | ${exp.started_at || "?"}`;
        select.appendChild(opt);
    });
}

function updateButton() {
    const v1 = select1.value;
    const v2 = select2.value;
    genBtn.disabled = !v1 || !v2 || v1 === v2;
}

fetch("/api/experiments/")
    .then((r) => r.json())
    .then((data) => {
        if (data.experiments) {
            fillSelect(select1, data.experiments);
            fillSelect(select2, data.experiments);
        }
    })
    .catch(() => {});

select1.addEventListener("change", updateButton);
select2.addEventListener("change", updateButton);

genBtn.addEventListener("click", function () {
    const id1 = parseInt(select1.value, 10);
    const id2 = parseInt(select2.value, 10);
    genBtn.disabled = true;
    genBtn.textContent = "Generating...";
    resultDiv.style.display = "none";

    fetch("/api/generate-compare-report/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": "{{ csrf_token }}",
        },
        body: JSON.stringify({
            experiment_id_1: id1,
            experiment_id_2: id2,
        }),
    })
        .then((r) => r.json())
        .then((data) => {
            if (data.success) {
                const reportUrl =
                    "/reports/view/" + data.report_url.replace(/\\/g, "/");
                resultDiv.innerHTML =
                    '<span style="color: #2e7d32;">Report generated! Reload page to see it';
                resultDiv.style.display = "block";
            } else {
                resultDiv.innerHTML =
                    '<span style="color: #c62828;">Error: ' +
                    (data.error || "unknown") +
                    "</span>";
                resultDiv.style.display = "block";
            }
        })
        .catch((err) => {
            resultDiv.innerHTML =
                '<span style="color: #c62828;">Request failed: ' +
                err.message +
                "</span>";
            resultDiv.style.display = "block";
        })
        .finally(() => {
            genBtn.disabled = false;
            genBtn.textContent = "Generate";
        });
});
