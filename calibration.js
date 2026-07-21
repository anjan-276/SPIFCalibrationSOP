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
for(const key in data){
    const element = document.getElementById(key);
    if(element){
        element.textContent = data[key];
    }
}