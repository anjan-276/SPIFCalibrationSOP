import { initializeApp } from
"https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";

import {
    getFirestore,
    collection,
    getDocs
} from
"https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

import {
    getAuth,
    onAuthStateChanged,
    signOut
} from
"https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const firebaseConfig = {
    apiKey: "AIzaSyBJU0eISC9PZQbUNY-vS8DK1hRwDMeFVDk",
    authDomain: "spifcalibrationdata.firebaseapp.com",
    projectId: "spifcalibrationdata",
    storageBucket: "spifcalibrationdata.firebasestorage.app",
    messagingSenderId: "119193036334",
    appId: "1:119193036334:web:ec607848b74e054d3521bf",
    measurementId: "G-DWMQZXKFJ9"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

onAuthStateChanged(auth, (user) => {

    if (!user) {
        window.location.href = "login.html";
    }

});

function displayCalibrationData(data){

    const tbody =
        document.getElementById(
            "calibrationBody"
        );

    
}

window.loadCalibration = async function () {

    const vin =
        document.getElementById("vinInput")
        .value
        .trim();

    if (!vin) {

        alert("Enter VIN");
        return;

    }

    try {

        const calibrationRef =
            collection(
                db,
                "trucks",
                vin,
                "calibrations"
            );

        const snapshot =
            await getDocs(calibrationRef);

        if (snapshot.empty) {

            document.getElementById(
                "calibrationData"
            ).textContent =
                "No calibration found";

            return;

        }

        let latestDoc = null;
        let latestDate = null;

        snapshot.forEach((doc) => {

            let dateString = doc.id;

            let docDate =
                new Date(
                    dateString
                        .replaceAll("\\", "/")
                        .replace(
                            /(\d{4})\/(\d{2})\/(\d{2})-(\d{2}):(\d{2}):(\d{2})/,
                            "$1-$2-$3T$4:$5:$6"
                        )
                );

            if (
                latestDate === null ||
                docDate > latestDate
            ) {

                latestDate = docDate;
                latestDoc = doc;

            }

        });

        if (latestDoc) {
            sessionStorage.setItem(
            "calibrationData",
            JSON.stringify(
            latestDoc.data()
        )
);

window.location.href =
    "calibration.html";

        }

    }
    catch (error) {

        console.error(error);

        document.getElementById(
            "calibrationData"
        ).textContent =
            "Error loading data";

    }

};

window.logout = function () {

    signOut(auth)
        .then(() => {

            window.location.href =
                "login.html";

        });

};