document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const searchForm = document.getElementById('search-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const typingIndicator = document.getElementById('typing-indicator');
    const convIdInput = document.getElementById('conv-id');
    const resetBtn = document.getElementById('reset-filters');

    const emotionEmojis = {
        'happy': '😊',
        'angry': '😡',
        'frustrated': '😞',
        'excited': '🤩',
        'confused': '😕',
        'neutral': '😐'
    };

    console.log("[DEBUG] Advanced Chat Platform JS Initialized.");

    // Initial load
    if (convIdInput) {
        loadMessages(convIdInput.value);
    }

    // --- Search & Filters ---
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const q = document.getElementById('search-q').value;
            const sentiment = document.getElementById('filter-sentiment').value;
            const emotion = document.getElementById('filter-emotion').value;
            loadMessages(convIdInput.value, q, sentiment, emotion);
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            searchForm.reset();
            loadMessages(convIdInput.value);
        });
    }

    // --- Chat Logic ---
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const messageText = chatInput.value.trim();
            if (!messageText) return;

            chatInput.value = '';
            // 1. Append user message immediately (Optimistic UI)
            const userMsgElement = appendMessage('user', { 
                text: messageText, 
                timestamp: getCurrentTime() 
            });
            
            showTyping(true);
            scrollToBottom();

            // 2. Send to server
            fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageText, conversation_id: convIdInput.value }),
            })
            .then(res => res.json())
            .then(data => {
                showTyping(false);
                if (data.error) return alert(data.error);
                
                // 3. Update the optimistic user message with real data (Sentiment/Emotion/Confidence)
                updateMessageMetadata(userMsgElement, data.user_message);
                
                // 4. Append bot response
                appendMessage('bot', data.bot_message);
                scrollToBottom();
            })
            .catch(err => {
                showTyping(false);
                console.error("[ERROR] Send failed:", err);
            });
        });
    }

    function loadMessages(conversationId, q='', sentiment='', emotion='') {
        let url = `/get_messages/${conversationId}?q=${q}&sentiment=${sentiment}&emotion=${emotion}`;
        fetch(url)
            .then(res => res.json())
            .then(messages => {
                chatMessages.innerHTML = '';
                messages.forEach(msg => {
                    appendMessage(msg.sender, {
                        text: msg.message,
                        timestamp: msg.timestamp,
                        sentiment: msg.sentiment,
                        emotion: msg.emotion,
                        confidence: msg.confidence,
                        ticket: msg.ticket
                    });
                });
                typingIndicator.classList.add('d-none');
                chatMessages.appendChild(typingIndicator);
                scrollToBottom();
            })
            .catch(err => console.error("[ERROR] History load failed:", err));
    }

    function appendMessage(sender, data) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        
        msgDiv.innerHTML = `
            <div class="msg-text">${data.text}</div>
            <div class="metadata-area mt-1"></div>
            <div class="small mt-1 ${sender === 'user' ? 'text-white-50' : 'text-muted'}" style="font-size: 0.65rem;">
                ${data.timestamp}
            </div>
        `;
        
        // If data already contains metadata (historical messages), render it
        if (sender === 'user' && (data.sentiment || data.emotion)) {
            const metaArea = msgDiv.querySelector('.metadata-area');
            renderMetadata(metaArea, data);
        }

        chatMessages.appendChild(msgDiv);
        if (!typingIndicator.classList.contains('d-none')) {
            chatMessages.appendChild(typingIndicator);
        }
        return msgDiv;
    }

    function updateMessageMetadata(element, data) {
        if (!element || !data) return;
        const metaArea = element.querySelector('.metadata-area');
        if (metaArea) {
            renderMetadata(metaArea, data);
        }
    }

    function renderMetadata(container, data) {
        let badges = '';
        if (data.sentiment) {
            badges += `<span class="sentiment-badge sentiment-${data.sentiment}">${data.sentiment.toUpperCase()}</span>`;
        }
        if (data.emotion) {
            const emoji = emotionEmojis[data.emotion] || '';
            badges += `<span class="emotion-badge">${data.emotion.toUpperCase()} ${emoji}</span>`;
        }
        
        let confidenceHtml = '';
        if (data.confidence) {
            confidenceHtml = `<div class="confidence-text small mt-1" style="font-size: 0.6rem; opacity: 0.8;">Confidence: ${data.confidence}%</div>`;
        }

        let ticketHtml = '';
        if (data.ticket) {
            ticketHtml = `<div class="ticket-badge mt-1"><span class="badge bg-danger" style="font-size: 0.6rem;">Ticket: ${data.ticket}</span></div>`;
        }

        container.innerHTML = `
            <div class="d-flex flex-wrap gap-1 align-items-center">${badges}</div>
            ${confidenceHtml}
            ${ticketHtml}
        `;
    }

    function showTyping(show) {
        if (show) {
            typingIndicator.classList.remove('d-none');
            chatMessages.appendChild(typingIndicator);
        } else {
            typingIndicator.classList.add('d-none');
        }
    }

    function scrollToBottom() { 
        chatMessages.scrollTop = chatMessages.scrollHeight; 
    }

    function getCurrentTime() {
        const now = new Date();
        return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    }
});
