const baseUrl = "http://127.0.0.1:7000";
// http://127.0.0.1:7000
// https://antoncopiloto.pythonanywhere.com
// Function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');
    let autosaveTimer;

// Debounced autosave function (waits 3 seconds after the last change)
function debouncedAutosave() {
    clearTimeout(autosaveTimer); // Clear the previous timer
    autosaveTimer = setTimeout(saveChanges, 3000); // Set a new timer for 3 seconds
}

// Function to perform save (used for both autosave and manual save)
function debouncedAutosave() {
    clearTimeout(autosaveTimer); // Clear the previous timer
    autosaveTimer = setTimeout(saveChanges, 3000); // Set a new timer for 3 seconds
}

function saveChanges() {
    var name = document.getElementById('name').value;
    var description = tinymce.get('description').getContent();
    var contractId = document.getElementById('description').dataset.contractId;
    var url = `${baseUrl}/api/contract-update/${contractId}/`;

    fetch(url, {
        method: 'PUT',
        headers: {
            'Content-type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({
            'name': name,
            'description': description
        })
    })
    .then(function (response) {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(function (data) {
        console.log('Save Success:', data);
    })
    .catch(function (error) {
        console.error('Save Error:', error);
    });
}

document.getElementById('description').addEventListener('input', debouncedAutosave);

// Initialize TinyMCE for the description field
tinymce.init({
    selector: '#description',
    plugins: 'advlist autolink lists link image charmap print preview anchor searchreplace visualblocks code fullscreen insertdatetime media table paste help wordcount',
    toolbar: 'undo redo | formatselect | bold italic underline strikethrough | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | code fullscreen',
    menubar: 'file edit view insert format tools table help',
    height: '85vh',
    width: '100%',
    language: 'es_MX',
    language_url: '/static/tinymce/langs/es_MX.js',
    language_load: true,
    setup: function (editor) {
        editor.on('init', function () {
            // Set the initial content to the textarea's value
            var initialContent = document.getElementById('description').value;
            editor.setContent(initialContent);
            editor.getContainer().style.width = '100%'; // Ensures the editor container fills its parent
        });

        // Detect text selection and display it in the HTML element
        editor.on('mouseup keyup', function () {
            const selectedText = editor.selection.getContent({ format: 'text' }).trim();
            const highlightDisplay = document.getElementById('highlightDisplay');
            const templateButtons = document.querySelector('.template-buttons'); // Get the template buttons container

            // Ensure element exists before trying to set textContent
            if (highlightDisplay) {
                if (selectedText) {
                    // Display the highlighted text and show template buttons
                    highlightDisplay.textContent = selectedText;
                    templateButtons.style.display = 'block'; // Show template buttons
                } else {
                    // Clear the display and hide template buttons if no text is selected
                    highlightDisplay.textContent = '';
                    templateButtons.style.display = 'none'; // Hide template buttons
                }
            }
        });

        // Attach debounced autosave to TinyMCE's input and change events
        editor.on('input', function () {
            debouncedAutosave(); // Trigger autosave on input events
        });
        editor.on('change', function () {
            debouncedAutosave(); // Trigger autosave on change events
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const copyButton = document.getElementById('copy-button'); // Ensure you have a button with this ID in your HTML

    copyButton.addEventListener('click', function() {
        const editorContent = tinymce.get('description').getContent({format: 'html'}); // Get HTML content from TinyMCE
        const data = new ClipboardItem({
            "text/html": new Blob([editorContent], {type: "text/html"})
        });

        navigator.clipboard.write([data]).then(function() {
            console.log('Successfully copied to clipboard');
        }).catch(function(error) {
            console.error('Could not copy text: ', error);
        });
    });
});

// Add an event listener to clear highlighted text when the highlight display is clicked
const highlightDisplay = document.getElementById('highlightDisplay');
const templateButtons = document.querySelector('.template-buttons'); // Template buttons container

highlightDisplay.addEventListener('click', function () {
    // Clear the highlighted text display and hide template buttons
    highlightDisplay.textContent = '';
    templateButtons.style.display = 'none'; // Hide template buttons

    // Clear selection in TinyMCE editor
    tinymce.activeEditor.selection.collapse();  // This collapses the selection (removes highlighted state)
});


// Event listener for the form submission
document.getElementById('contractProjectForm').addEventListener('submit', function (e) {
    e.preventDefault(); // Prevent the form from submitting the traditional way
    saveChanges(); // Manually trigger a save
});

// main.js (or your current file)
document.querySelectorAll('.template-button').forEach(button => {
    button.addEventListener('click', function () {
        var templateKey = this.getAttribute('data-template');
        var templateText = templates[templateKey] || ''; // Use the templates from templates.js

        var descriptionField = tinymce.get('description'); // Use TinyMCE instance if applicable

        if (descriptionField) {
            // Append the template text to the existing content if it exists
            var currentContent = descriptionField.getContent();
            descriptionField.setContent(currentContent + ' ' + templateText);
        } else {
            // Fallback for plain textarea
            var textarea = document.getElementById('description');
            textarea.value += ' ' + templateText;
        }

        // Check and clear aiInput if it contains specific template names
        var aiInputField = document.getElementById('aiInput');
        if (aiInputField) {
            setTimeout(function() {
                const invalidNames = Array.from({ length: 28 }, (_, i) => `template${i + 1}`);
                if (invalidNames.some(name => aiInputField.value.includes(name))) {
                    aiInputField.value = ''; // Clear aiInput if it contains specific names
                }
            }, 50); // 50ms delay to allow name rendering before clearing
        }
    });
});

var searchInput = document.getElementById('templateSearch');
if (searchInput) {
    searchInput.addEventListener('input', function () {
        var searchQuery = this.value.toLowerCase();
        var templates = document.querySelectorAll('.template-card');
        console.log("Found template cards: ", templates.length); // Check how many cards are found

        templates.forEach(function (templateCard) {
            var templateName = templateCard.getAttribute('data-template-name').toLowerCase();
            if (templateName.includes(searchQuery)) {
                templateCard.style.display = 'block';
            } else {
                templateCard.style.display = 'none';
            }
        });
    });
} else {
    console.error("Search input not found");
}

// -----------------------------------------------------------
// --------------- Side panel text messages ------------------
// -----------------------------------------------------------
const openSubtaskPopupButton = document.getElementById('openSubtaskPopup');
const popup = document.getElementById('createSubtaskPopup');
const mainContent = document.querySelector('.main-content');
let isPopupActive = false;

// Open the side panel and dynamically set the data-contract-id attribute
openSubtaskPopupButton.addEventListener('click', function() {
    if (isPopupActive) {
        return; // Prevent multiple popup actions while one is active
    }

    const contractProjectId = this.getAttribute('data-contract-id'); // Get the project ID from the button's data attribute
    if (contractProjectId) {
        isPopupActive = true; 
        popup.setAttribute('data-contract-id', contractProjectId);  // Set the project ID on the popup
        console.log('Subtask popup opened with Contract Project ID:', contractProjectId);  // Log the correct ID
        popup.classList.add('active');
        mainContent.style.marginRight = '30%';

        // Add a slight delay to ensure the chat history container has rendered before scrolling
        setTimeout(function() {
            const chatHistoryContainer = document.getElementById('chatHistoryContainer');
            if (chatHistoryContainer) {
                chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight; // Scroll to the bottom
            }
        }, 300);  // Delay by 300ms (can adjust this if needed)

        // Fetch chat history after opening the popup
        fetch(`/api/get-chat-history-contract/${contractProjectId}/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Full Response Data:', data);  // Log the full response data

            if (data.chat_history) {
                console.log('Chat History:', data.chat_history);  // Log chat history to console

                const chatHistoryContainer = document.getElementById('chatHistoryContainer');
                chatHistoryContainer.innerHTML = '';  // Clear any existing chat history

                data.chat_history.forEach(chat => {
                    const chatMessage = document.createElement('div');
                    chatMessage.classList.add('message', 'ai-message');

                    let highlightHTML = '';
                    if (chat.highlighted_text) {
                        highlightHTML = `<div><span class="highlight">${chat.highlighted_text}</span></div>`;
                    }

                    // Apply Markdown parsing for formatted display of AI response
                    const formattedResponse = marked.parse(chat.ai_response);  // Format saved response with Markdown

                    chatMessage.innerHTML = `
                        <div class="chat-bubble user-bubble">
                            ${highlightHTML}
                            <div>${chat.instruction}</div>
                        </div>
                        <div class="chat-bubble ai-bubble">
                            <div id="aiResponse_${chat.id}">${formattedResponse}</div>
                            <button class="copy-button btn btn-outline-light btn-sm" data-response-id="aiResponse_${chat.id}" title="Copy AI response">
                                <i class="align-middle me-2 far fa-fw fa-clipboard"></i>
                            </button>
                            <button class="read-button btn btn-outline-light btn-sm" data-response-id="aiResponse_${chat.id}" title="Read AI response">
                                <i class="fas fa-volume-up"></i>
                            </button>
                        </div>
                    `;

                    // Append the message to the chat history container
                    chatHistoryContainer.appendChild(chatMessage);
                });

                // Re-attach event listeners for dynamically added copy and read buttons
                attachEventListeners();

                // Scroll to the bottom after loading the messages
                setTimeout(function() {
                    chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight; 
                }, 300);  // Delay to ensure rendering is complete before scrolling
            } else {
                console.log('No chat history found.');
            }
            isPopupActive = false; 
        })
        .catch(error => {
            console.error('Error fetching chat history:', error);
            isPopupActive = false; // Reset state on error
        });

    } else {
        console.error('Contract Project ID is not defined in the button');
    }
});

// Function to attach copy and read button event listeners
function attachEventListeners() {
    // Attach copy event listeners
    const copyButtons = document.querySelectorAll('.copy-button');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const responseId = this.getAttribute('data-response-id');
            const aiResponse = document.getElementById(responseId).innerHTML; // Use innerHTML for rich text

            // Copy the AI response as rich text to the clipboard
            navigator.clipboard.write([
                new ClipboardItem({
                    "text/html": new Blob([aiResponse], { type: "text/html" }),
                    "text/plain": new Blob([document.getElementById(responseId).innerText], { type: "text/plain" })
                })
            ]).catch(err => {
                console.error('Failed to copy AI response: ', err);
            });
        });
    });

    // Attach read event listeners
    const readButtons = document.querySelectorAll('.read-button');
    readButtons.forEach(button => {
        let isSpeaking = false;  // Track if the speech is currently playing

        button.addEventListener('click', function() {
            const responseId = this.getAttribute('data-response-id');
            const aiResponse = document.getElementById(responseId).textContent;

            if (isSpeaking) {
                // Stop the current speech
                window.speechSynthesis.cancel();
                isSpeaking = false;
                this.innerHTML = '<i class="fas fa-volume-up"></i>'; // Change icon back to "Read"
            } else {
                // Use Web Speech API to read the text aloud
                const utterance = new SpeechSynthesisUtterance(aiResponse);
                utterance.lang = 'es-ES'; // Set the language to Spanish (Spain), or use 'es-MX' for Mexican Spanish

                // Set an event listener to update the button once speech ends
                utterance.onend = () => {
                    isSpeaking = false;
                    this.innerHTML = '<i class="fas fa-volume-up"></i>'; // Change icon back to "Read"
                };

                window.speechSynthesis.speak(utterance);
                isSpeaking = true;
                this.innerHTML = '<i class="fas fa-stop"></i>'; // Change icon to "Stop"
            }
        });
    });
}

// Close the side panel
const closePopupButton = document.getElementById('closePopup');
closePopupButton.addEventListener('click', function() {
    popup.classList.remove('active');
    mainContent.style.marginRight = '0';
    isPopupActive = false; 
});

// Send AI request and display response
const aiSendButton = document.getElementById('aiSend');
aiSendButton.addEventListener('click', function() {
    sendMessage(); // Only call sendMessage from here
});

function sendMessage() {
    if (isPopupActive) {
        console.log("Another action is in progress. Please wait.");
        return; // Prevent sending a new message while another action is ongoing
    }

    isPopupActive = true; 

    const contractProjectId = popup.getAttribute('data-contract-id');
    const highlightedText = document.getElementById('highlightDisplay').textContent.trim() || '';  // Default to empty string if no highlight
    const instruction = textarea.value.trim();  // Trim user input to avoid empty space submission

    // Check if both fields are empty
    if (!highlightedText && !instruction) {
        console.log("Nothing to send, both highlighted text and instruction are empty.");
        isPopupActive = false; 
        return;
    }

    // Append the user's message immediately to the chat history
    const chatHistoryContainer = document.getElementById('chatHistoryContainer');
    const userMessage = document.createElement('div');
    userMessage.classList.add('message');  // Same structure as history
    let highlightHTML = '';
    if (highlightedText) {
        highlightHTML = `<div><span class="highlight">${highlightedText}</span></div>`;
    }
    userMessage.innerHTML = `
        <div class="chat-bubble user-bubble">
            ${highlightHTML}
            <div>${instruction}</div>
        </div>
    `;
    chatHistoryContainer.appendChild(userMessage);

    // Display the loading message
    const loadingMessageId = `loading-message-${Date.now()}`;
    const loadingMessageHTML = `
        <div class="chat-bubble ai-bubble loading" id="${loadingMessageId}">
            <span class="skeleton-line"></span>
            <span class="skeleton-line"></span>
            <span class="skeleton-line"></span>
        </div>
    `;
    chatHistoryContainer.insertAdjacentHTML('beforeend', loadingMessageHTML);

    // Scroll to the bottom to show the loading indicator
    chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;

    // Clear the input field after sending the message
    textarea.value = '';
    textarea.style.height = 'auto'; // Reset height

    // Clear the highlight display and hide template buttons after sending
    document.getElementById('highlightDisplay').textContent = '';  // Clear highlighted text
    document.querySelector('.template-buttons').style.display = 'none';  // Hide template buttons

    // Make the API call to submit the message
    fetch(`${baseUrl}/api/create-ai-chat-contract/${contractProjectId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({
            highlighted_text: highlightedText,  // This could be empty
            instruction: instruction            // This will not be empty after the trim check
        })
    })
    .then(response => response.json())
    .then(data => {
        // Remove the loading message
        document.getElementById(loadingMessageId).remove();

        // Create a unique ID for this AI message
        const uniqueId = `aiResponse_${data.id}_${Date.now()}`; // Use data.id and a timestamp to ensure uniqueness

        // Parse the AI response into formatted HTML
        const formattedResponse = marked.parse(data.ai_response);

        // Create the AI message container
        const aiMessage = document.createElement('div');
        aiMessage.classList.add('message');  // Match the history structure

        aiMessage.innerHTML = `
            <div class="chat-bubble ai-bubble">
                <div id="${uniqueId}"></div> <!-- Empty container for typing effect -->
                <button class="copy-button btn btn-outline-light btn-sm" data-response-id="${uniqueId}" title="Copy AI response">
                    <i class="align-middle me-2 far fa-fw fa-clipboard"></i>
                </button>
                <button class="read-button btn btn-outline-light btn-sm" data-response-id="${uniqueId}" title="Read AI response">
                    <i class="fas fa-volume-up"></i>
                </button>
            </div>
        `;

        // Append the AI message bubble to the chat history container
        chatHistoryContainer.appendChild(aiMessage);

        // Implement the typing effect with HTML content
        let i = 0;
        const responseElement = document.getElementById(uniqueId);  // Target the container with uniqueId
        const speed = 5; // Typing speed in milliseconds

        function typeWriter() {
            // Use innerHTML to add progressively from formattedResponse's HTML content
            responseElement.innerHTML = formattedResponse.slice(0, i);
            i++;

            // Scroll to the bottom with each new character
            chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;

            if (i <= formattedResponse.length) {
                setTimeout(typeWriter, speed);
            } else {
                isPopupActive = false; // Reset state after the typing effect is complete
            }
        }

        typeWriter(); // Start the typing effect

        // Add copy event listener to the new copy button
        const copyButton = aiMessage.querySelector('.copy-button');
        copyButton.addEventListener('click', function() {
            const responseId = this.getAttribute('data-response-id');
            const aiResponse = document.getElementById(responseId).innerHTML; // Use innerHTML for rich text

            // Copy the AI response as rich text to the clipboard
            navigator.clipboard.write([
                new ClipboardItem({
                    "text/html": new Blob([aiResponse], { type: "text/html" }),
                    "text/plain": new Blob([document.getElementById(responseId).innerText], { type: "text/plain" })
                })
            ]).catch(err => {
                console.error('Failed to copy AI response: ', err);
            });
        });

        // Add read event listener to the new read button
        const readButton = aiMessage.querySelector('.read-button');
        let isSpeaking = false; // Track if the speech is currently playing

        readButton.addEventListener('click', function() {
            if (isSpeaking) {
                // Stop the current speech
                window.speechSynthesis.cancel();
                isSpeaking = false;
                readButton.innerHTML = '<i class="fas fa-volume-up"></i>'; // Change icon back to "Read"
            } else {
                const responseId = this.getAttribute('data-response-id');
                const aiResponse = document.getElementById(responseId).textContent;

                // Use Web Speech API to read the text aloud in Spanish
                const utterance = new SpeechSynthesisUtterance(aiResponse);
                utterance.lang = 'es-ES'; // Set the language to Spanish (Spain), or use 'es-MX' for Mexican Spanish
                
                // Set an event listener to update the button once speech ends
                utterance.onend = function() {
                    isSpeaking = false;
                    readButton.innerHTML = '<i class="fas fa-volume-up"></i>'; // Change icon back to "Read"
                };

                window.speechSynthesis.speak(utterance);
                isSpeaking = true;
                readButton.innerHTML = '<i class="fas fa-stop"></i>'; // Change icon to "Stop"
            }
        });

        // Scroll to the bottom after receiving the AI's message
        chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;
    })
    .catch(error => {
        console.error('Error:', error);
        isPopupActive = false; // Reset state on error
    });
}

// Function to auto-resize the textarea
const textarea = document.getElementById('aiInput');
textarea.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
});

// Listen for "Enter" key press to send message
textarea.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { // Check if Enter is pressed and Shift is not held down
        e.preventDefault(); // Prevent adding a new line in the textarea
        sendMessage(); // Call the function to send the message
    }
});


// Add event listener to template buttons outside the modal
document.querySelectorAll('.template-button').forEach(button => {
    button.addEventListener('click', function() {
        const templateText = this.getAttribute('data-template'); // Get the template text

        // Insert the template text into the textarea
        const textarea = document.getElementById('aiInput');
        textarea.value = templateText;

        // Optionally: Auto-focus on the textarea after inserting
        textarea.focus();
    });
});

// Add event listener to template buttons inside the modal
document.querySelectorAll('.modal-template-buttons .template-button').forEach(button => {
    button.addEventListener('click', function() {
        const templateText = this.getAttribute('data-template'); // Get the template text

        // Insert the template text into the textarea
        const textarea = document.getElementById('aiInput');
        textarea.value = templateText;

        // Optionally: Auto-focus on the textarea after inserting
        textarea.focus();

        // Close the modal after selecting a template
        const modal = bootstrap.Modal.getInstance(document.getElementById('templateModal')); // Bootstrap 5 modal instance
        modal.hide();
    });
});

window.addEventListener('load', function() {
    const chatHistoryContainer = document.getElementById('chatHistoryContainer');
    if (chatHistoryContainer) {
        chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight; // Scroll to the bottom
    }
});

document.getElementById('deleteChatButton').addEventListener('click', function() {
    if (confirm("Are you sure you want to delete this chat?")) { // Confirmation prompt
        const contractProjectId = this.getAttribute('data-contract-id');
        const url = `${baseUrl}/api/delete-chat-history-contract/${contractProjectId}/`;

        fetch(url, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrftoken,
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert(data.message); // Success message
                // Optionally clear the chat history display in the UI
                document.getElementById('chatHistoryContainer').innerHTML = '';
            } else if (data.error) {
                alert(data.error); // Error message
            }
        })
        .catch(error => console.error('Error deleting chat history:', error));
    }
});

