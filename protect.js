import { initializeApp } from 
"https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";


import {
getAuth,
onAuthStateChanged
}
from
"https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";


const firebaseConfig = {

apiKey:"YOUR_API_KEY",
authDomain:"YOUR_PROJECT.firebaseapp.com",
projectId:"YOUR_PROJECT_ID"

};


const app = initializeApp(firebaseConfig);

const auth = getAuth(app);



onAuthStateChanged(
    auth,
    (user)=>{

        if(!user){

            window.location.href =
            "login.html";

        }

    }
);