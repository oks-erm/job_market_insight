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

    let name = document.getElementById('name').value;
    let email = document.getElementById('email').value;
    let message = document.getElementById('message').value;

    if (!validateFormData(name, email, message)) {
        return; 
    }

    displayLoadingFeedback(); 
    
    let formData = { name, email, message };

    fetch('/process-contact-form', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
    })
    .then(response => {
        // Check if the response is JSON
        const contentType = response.headers.get('content-type');
        if (!response.ok) {
            if (contentType && contentType.includes('application/json')) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Computer says no. Unknown error.');
                });
            } else {
                // Handle non-JSON responses
                return response.text().then(text => {
                    console.error('Non-JSON response:', text);
                    // throw new Error('Server error occurred. Please try again.');
                });
            }
        }
        return response.json();
    })
    .then(data => {
        displayFeedback(true, data.message);
        resetForm();
    })
    .catch((error) => {
        console.error('Error:', error);
        displayFeedback(false, error.message);
    });
});


function validateFormData(name, email, message) {
    // Name validation
    if (!name.trim()) {
        displayFeedback(false, 'Name is required.');
        return false;
    }

    // Email validation
    if (!email.trim()) {
        displayFeedback(false, 'Email is required.');
        return false;
    } else if (!validateEmail(email)) {
        displayFeedback(false, 'Please enter a valid email address.');
        return false;
    }

    // Message validation
    if (!message.trim()) {
        displayFeedback(false, 'Message is required.');
        return false;
    }

    return true;
}


function validateEmail(email) {
    var regex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
    return regex.test(email);
}


function displayFeedback(isSuccess, message) {
    let feedbackElement = document.getElementById('formFeedback');
    feedbackElement.innerHTML = message;
    feedbackElement.classList.remove('error', 'loading');

    if (isSuccess) {
        feedbackElement.classList.add('success');
    } else {
        feedbackElement.classList.add('error');
    }

    feedbackElement.style.display = 'block';
    feedbackElement.scrollIntoView({ behavior: 'smooth' });
}

function displayLoadingFeedback() {
    let feedbackElement = document.getElementById('formFeedback');
    feedbackElement.innerHTML = 'Sending message...';
    feedbackElement.classList.remove('error', 'success');
    feedbackElement.classList.add('loading');
    feedbackElement.style.display = 'block';
}

function resetForm() {
    document.getElementById('contactForm').reset();
}