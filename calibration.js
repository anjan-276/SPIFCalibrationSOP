const data =
    JSON.parse(
        sessionStorage.getItem(
            "calibrationData"
        )
    );
if(!data){
    alert("No calibration data found");
    window.location.href = "technician.html";
}

// Fields that may be stored either as a single combined total (e.g. "emFrWtUp")
// or as separate left/right sensor readings (e.g. "emFrWtUpL" / "emFrWtUpR")
// that need to be summed.
const AXLE_WEIGHT_FIELDS = [
    "emFrWtUp", "emFrWtDw",
    "emFrTanWtUp", "emFrTanWtDw",
    "emRearTanWtUp", "emRearTanWtDw",
    "emLiftWt",
    "ldFrWtUp", "ldFrWtDw",
    "ldFrTanWtUp", "ldFrTanWtDw",
    "ldRearTanWtUp", "ldRearTanWtDw",
    "ldLiftWt"
];

function resolveAxleWeight(data, field) {
    const left = data[field + "L"];
    const right = data[field + "R"];
    if (data[field] !== undefined && data[field] !== null) {
        return { total: data[field], left, right };
    }
    if (left !== undefined && right !== undefined) {
        return { total: left + right, left, right };
    }
    return { total: undefined, left: undefined, right: undefined };
}

for (const field of AXLE_WEIGHT_FIELDS) {
    const { total, left, right } = resolveAxleWeight(data, field);
    const element = document.getElementById(field);
    if (!element || total === undefined) continue;

    element.textContent = "";
    element.appendChild(document.createTextNode(String(total)));
    if (left !== undefined && right !== undefined) {
        const breakdown = document.createElement("span");
        breakdown.className = "lr-breakdown";
        breakdown.textContent = `L: ${left} / R: ${right}`;
        element.appendChild(document.createElement("br"));
        element.appendChild(breakdown);
    }
}

for (const key in data) {
    if (AXLE_WEIGHT_FIELDS.includes(key)) continue;
    if (/[LR]$/.test(key) && AXLE_WEIGHT_FIELDS.includes(key.slice(0, -1))) continue;
    const element = document.getElementById(key);
    if (element) {
        element.textContent = data[key];
    }
}