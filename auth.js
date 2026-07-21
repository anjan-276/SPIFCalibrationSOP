import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
    getAuth,
    signInWithEmailAndPassword
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

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
const auth = getAuth(app);
window.login = function(){
    let email = document.getElementById("email").value;
    let password = document.getElementById("password").value;
    signInWithEmailAndPassword(
        auth,
        email,
        password
    )
    .then(()=>{
        window.location.href =
        "technician.html";
    })
    .catch((error)=>{
        document.getElementById(
            "message"
        ).innerHTML =
        error.message;
    });
};