document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('contactBtn').addEventListener('click', function () {
        let formContainer = document.getElementById('contactFormContainer');
        let contactBtn = document.getElementById('contactBtn');

        if (formContainer.style.display === "none") {
            // Show the form
            formContainer.style.display = "block";
            contactBtn.textContent = "Hide Form";
            contactBtn.classList.add('narrow-btn');
            // Scroll to the form
            formContainer.scrollIntoView({ behavior: 'smooth' });
        } else {
            // Hide the form
            formContainer.style.display = "none";
            contactBtn.textContent = "Contact Me";
            contactBtn.classList.remove('narrow-btn');
        }
    });
});

document.getElementById('contactForm').addEventListener('submit', function (event) {
    event.preventDefault();

    let formData = {
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        message: document.getElementById('message').value
    };

    fetch('/process-contact-form', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            displayFeedback(true, 'Thank you for your message!');
            resetForm();
        })
        .catch((error) => {
            displayFeedback(false, 'There was a problem sending your message.');
            console.error('Error:', error);
        });
});


function displayFeedback(isSuccess, message) {
    let feedbackElement = document.getElementById('formFeedback');
    feedbackElement.innerHTML = message;
    feedbackElement.classList.remove('error');

    if (!isSuccess) {
        feedbackElement.classList.add('error');
    }

    feedbackElement.style.display = 'block';
}

function resetForm() {
    document.getElementById('contactForm').reset();
}