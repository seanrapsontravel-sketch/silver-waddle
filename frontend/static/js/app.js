// Global state
let currentMat = null;
const API_BASE = '';

// DOM elements
const matSelectionView = document.getElementById('mat-selection');
const chatView = document.getElementById('chat-view');
const matsList = document.getElementById('mats-list');
const backButton = document.getElementById('back-button');
const matLogo = document.getElementById('mat-logo');
const matName = document.getElementById('mat-name');
const chatForm = document.getElementById('chat-form');
const questionInput = document.getElementById('question-input');
const sendButton = document.getElementById('send-button');
const chatMessages = document.getElementById('chat-messages');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadMATs();
    setupEventListeners();
});

// Event listeners
function setupEventListeners() {
    backButton.addEventListener('click', () => {
        showMatSelection();
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (question) {
            await askQuestion(question);
            questionInput.value = '';
        }
    });

    // Allow Enter to submit (Shift+Enter for new line)
    questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
}

// Load MATs
async function loadMATs() {
    try {
        const response = await fetch(`${API_BASE}/api/mats`);
        const mats = await response.json();
        
        matsList.innerHTML = '';
        mats.forEach(mat => {
            const card = createMATCard(mat);
            matsList.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading MATs:', error);
        matsList.innerHTML = '<p style="text-align: center; color: #e74c3c;">Error loading MATs. Please refresh the page.</p>';
    }
}

// Create MAT card
function createMATCard(mat) {
    const card = document.createElement('div');
    card.className = 'mat-card';
    card.addEventListener('click', () => selectMAT(mat));
    
    const logo = document.createElement('img');
    logo.className = 'mat-card-logo';
    logo.src = mat.logo_url || '/static/logos/default-logo.svg';
    logo.alt = `${mat.name} Logo`;
    logo.onerror = function() {
        this.src = '/static/logos/default-logo.svg';
    };
    
    const name = document.createElement('div');
    name.className = 'mat-card-name';
    name.textContent = mat.name;
    
    card.appendChild(logo);
    card.appendChild(name);
    
    return card;
}

// Select MAT
function selectMAT(mat) {
    currentMat = mat;
    matLogo.src = mat.logo_url || '/static/logos/default-logo.svg';
    matLogo.onerror = function() {
        this.src = '/static/logos/default-logo.svg';
    };
    matName.textContent = mat.name;
    
    // Clear previous messages except the welcome message
    chatMessages.innerHTML = `
        <div class="message assistant-message">
            <div class="message-content">
                <p>Hello! I can answer questions about ${mat.name} based on their newsletters. What would you like to know?</p>
            </div>
        </div>
    `;
    
    showChatView();
}

// Show views
function showMatSelection() {
    matSelectionView.classList.remove('hidden');
    chatView.classList.add('hidden');
    currentMat = null;
}

function showChatView() {
    matSelectionView.classList.add('hidden');
    chatView.classList.remove('hidden');
    questionInput.focus();
}

// Ask question
async function askQuestion(question) {
    if (!currentMat) return;
    
    // Add user message
    addMessage('user', question);
    
    // Disable input
    questionInput.disabled = true;
    sendButton.disabled = true;
    sendButton.innerHTML = '<div class="loading"></div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                mat_id: currentMat.id,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        addMessage('assistant', data.answer);
    } catch (error) {
        console.error('Error asking question:', error);
        addMessage('assistant', 'Sorry, I encountered an error while processing your question. Please try again.');
    } finally {
        // Re-enable input
        questionInput.disabled = false;
        sendButton.disabled = false;
        sendButton.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
        `;
        questionInput.focus();
    }
}

// Add message to chat
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Parse markdown links and convert to HTML
    const parsedContent = parseMarkdownLinks(content);
    
    const p = document.createElement('p');
    p.innerHTML = parsedContent;
    
    contentDiv.appendChild(p);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Parse markdown links [text](url) to HTML links
function parseMarkdownLinks(text) {
    // Escape HTML first to prevent XSS
    let escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Convert markdown links [text](url) to HTML links
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    return escaped.replace(linkRegex, (match, text, url) => {
        // Only allow http/https URLs for security
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="source-link">${text}</a>`;
        }
        return match;
    });
}

