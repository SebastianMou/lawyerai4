document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const messageWrapper = document.getElementById('list-wrapper-messages');
    let isGeneratingResponse = false;

    // Define isSpeaking at the top to track the speaking state globally
    let isSpeaking = false;

    function loadChatHistory() {
        fetch(`${baseUrl}/api/chatsessions/${sessionId}/`)
            .then(response => response.json())
            .then(function(data) {
                messageWrapper.innerHTML = '';
                data.messages.forEach(function(message) {
                    const formattedContent = formatMessageContent(message.content);
                    const uniqueId = `message-${message.id}`;
                    const messageHTML = `
                        <div class="${message.sender === 'user' ? 'user-message' : 'ai-message'}" id="${uniqueId}">
                            <div>
                                <span class="message-text-content" id="${uniqueId}-text">${formattedContent}</span>
                            </div>
                            ${message.sender === 'AI' ? `
                                <button onclick="copyToClipboard('${uniqueId}-text')" class="copy-button">
                                    <i class="align-middle me-2 far fa-fw fa-clipboard"></i>copiar
                                </button>
                                <button data-text-id="${uniqueId}-text" class="read-button">
                                    <span id="${uniqueId}-icon"><i style="color: white;" class="align-middle me-2 fas fa-volume-up"></i></span>Leer
                                </button>
                            ` : ''}
                        </div>
                    `;
                    messageWrapper.insertAdjacentHTML('beforeend', messageHTML);
                });
                scrollToBottom();
            })
            .catch(error => console.error('Error fetching chat history:', error));
    }

    // Helper function to scroll with a slight delay for smoother experience
    function smoothScrollToBottom() {
        setTimeout(() => {
            messageWrapper.scrollTop = messageWrapper.scrollHeight;
        }, 100); // Small delay for smoother transition
    }

    // Helper function to observe only message content text for each message
    function observeMessageContent(element) {
        const observer = new MutationObserver((mutationsList) => {
            for (const mutation of mutationsList) {
                if (mutation.type === "characterData") {
                    scrollToBottom();
                    break;
                }
            }
        });
        observer.observe(element, { characterData: true, subtree: true });
    }

    // Scroll to the bottom function
    function scrollToBottom() {
        messageWrapper.scrollTop = messageWrapper.scrollHeight;
    }

    function typeMessageEffect(elementId, formattedText, speed = 2) {
        const element = document.getElementById(elementId);
        element.innerHTML = ""; // Clear the element before starting typing effect

        let index = 0;

        function typeWriter() {
            if (index < formattedText.length) {
                // Append the next chunk of characters as HTML (interpreting HTML tags correctly)
                element.innerHTML = formattedText.substring(0, index + 4);
                index += 4;

                // Set a delay for the next chunk
                setTimeout(typeWriter, speed);

                // Scroll to bottom during typing
                smoothScrollToBottom();
            } else {
                // Final scroll to ensure visibility at the end of typing
                smoothScrollToBottom();
            }
        }

        // Start the typing effect
        typeWriter();
    }

    function formatMessageContent(content) {
        // Use the marked library to convert markdown to HTML
        return marked.parse(content);
    }

    loadChatHistory();

    const textarea = document.getElementById('chat-input');

    // Auto-resize the textarea as the user types
    textarea.addEventListener('input', function() {
        this.style.height = 'auto'; // Reset height
        this.style.height = this.scrollHeight + 'px'; // Expand based on scroll height
    });

    // Optional: Limit maximum height for the textarea
    textarea.style.maxHeight = '150px'; // Prevent it from growing too large

    // Listen for the Enter key on the textarea
    textarea.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Prevents a new line from being added
            form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true })); // Triggers form submit
        }
    });

    // Modified submit handler to use the typing effect
    form.addEventListener('submit', function(e) {
        e.preventDefault();
    
        if (isGeneratingResponse) {
            return; // Prevent form submission while AI is generating a response
        }
    
        // Immediately set isGeneratingResponse to true
        isGeneratingResponse = true;
        chatInput.disabled = true; // Disable input to prevent further user input
    
        const userMessage = chatInput.value;
        if (!userMessage.trim()) {
            isGeneratingResponse = false; // Reset state if input is empty
            chatInput.disabled = false;
            return;
        }
    
        const uniqueId = `user-message-${Date.now()}`;
        const userMessageHTML = `
            <div class="user-message" id="${uniqueId}">
                <span class="message-text" id="${uniqueId}-text">${userMessage}</span>
            </div>
        `;
        messageWrapper.insertAdjacentHTML('beforeend', userMessageHTML);
    
        chatInput.value = '';
        chatInput.style.height = 'auto';
        smoothScrollToBottom(); // Scroll down after user message
    
        // Display the loading message
        const loadingMessageId = `loading-message-${Date.now()}`;
        const loadingMessageHTML = `
            <div class="ai-message loading" id="${loadingMessageId}">
                <span class="skeleton-line"></span>
                <span class="skeleton-line"></span>
                <span class="skeleton-line"></span>
            </div>
        `;
        messageWrapper.insertAdjacentHTML('beforeend', loadingMessageHTML);
    
        smoothScrollToBottom(); // Scroll while loading is visible
    
        const data = { message: userMessage };
    
        fetch(`${baseUrl}/api/chatsessions/${sessionId}/send_message/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(function(data) {
            // Remove the loading message
            document.getElementById(loadingMessageId).remove();
    
            // Ensure messages are returned from the response
            if (!data.messages || data.messages.length === 0) {
                throw new Error('No messages returned from the server');
            }
    
            // Display the AI's response
            let aiContent = data.messages[data.messages.length - 1].content;
            aiContent = formatMessageContent(aiContent); // Format AI content with markdown
            const uniqueId = `ai-message-${Date.now()}`;
    
            // Create a container for the AI message
            const aiMessageHTML = `
                <div class="ai-message" id="${uniqueId}">
                    <span class="message-text" id="${uniqueId}-text"></span>
                    <div>
                        <button onclick="copyToClipboard('${uniqueId}-text')" class="copy-button">
                            <i class="align-middle me-2 far fa-fw fa-clipboard"></i>copiar
                        </button>
                        <button data-text-id="${uniqueId}-text" class="read-button">
                            <span id="${uniqueId}-icon"><i style="color: white;" class="align-middle me-2 fas fa-volume-up"></i></span>Leer
                        </button>
                    </div>
                </div>
            `;
            messageWrapper.insertAdjacentHTML('beforeend', aiMessageHTML);
    
            // Call typing effect function to display the AI response dynamically
            typeMessageEffect(`${uniqueId}-text`, aiContent);
    
            // Re-enable input and reset state
            isGeneratingResponse = false;
            chatInput.disabled = false;
            chatInput.focus();
        })
        .catch(error => {
            console.error('Error:', error);
            // Optionally remove the loading message if an error occurs
            document.getElementById(loadingMessageId).remove();
    
            // Re-enable input and reset state on error
            isGeneratingResponse = false;
            chatInput.disabled = false;
            chatInput.focus();
        });
    });
    

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

    function scrollToBottom() {
        messageWrapper.scrollTop = messageWrapper.scrollHeight;
    }

    messageWrapper.addEventListener('click', function(event) {
        if (event.target.closest('.read-button')) {
            const button = event.target.closest('.read-button');
            const elementId = button.getAttribute('data-text-id');
            toggleReadAloud(elementId);
        }
    });

    window.copyToClipboard = function(elementId) {
        const element = document.getElementById(elementId);
        const htmlToCopy = element.innerHTML; // Get the HTML content of the message

        // Use Clipboard API to write HTML directly to the clipboard
        navigator.clipboard.write([
            new ClipboardItem({
                "text/html": new Blob([htmlToCopy], { type: "text/html" }),
                "text/plain": new Blob([element.innerText], { type: "text/plain" })
            })
        ]).then(() => {
            console.log("Rich text copied successfully!");
        }).catch((error) => {
            console.error("Failed to copy text: ", error);
        });
    };

    function toggleReadAloud(elementId) {
        const iconElement = document.getElementById(`${elementId.replace('-text', '')}-icon`);

        if (isSpeaking) {
            window.speechSynthesis.cancel();
            isSpeaking = false;
            iconElement.innerHTML = '<i style="color: white;" class="align-middle me-2 fas fas fa-volume-up"></i>';
        } else {
            const textToRead = document.getElementById(elementId).innerText;
            const speech = new SpeechSynthesisUtterance(textToRead);
            speech.lang = 'es-ES';

            iconElement.innerHTML = '<i class="align-middle me-2 far fa-fw fa-pause-circle"></i>';

            speech.onend = () => {
                isSpeaking = false;
                iconElement.innerHTML = '<i style="color: white;" class="align-middle me-2 fas fas fa-volume-up"></i>';
            };

            window.speechSynthesis.speak(speech);
            isSpeaking = true;
        }
    }
});
