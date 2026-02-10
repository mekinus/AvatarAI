/* ══════════════════════════════════════════════════════════════
   AvatarAI Stream Overlay — JavaScript
   Conecta via WebSocket e renderiza chat + speech em tempo real
   ══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── Config ────────────────────────────────────────────────
    const CONFIG = {
        wsUrl: `ws://${window.location.hostname || 'localhost'}:8767`,
        maxChatMessages: 20,
        chatFadeAfterMs: 30000,      // fade mensagens antigas após 30s
        speechTypeSpeed: 30,          // ms por caractere no typewriter
        eventDisplayMs: 5000,         // tempo que evento fica na tela
        reconnectInterval: 3000,      // intervalo de reconexão
    };

    // ── DOM Elements ──────────────────────────────────────────
    const chatMessages = document.getElementById('chat-messages');
    const speechBox = document.getElementById('speech-box');
    const speechText = document.getElementById('speech-text');
    const topicBar = document.getElementById('topic-bar');
    const topicText = document.getElementById('topic-text');
    const eventAlert = document.getElementById('event-alert');
    const eventTitle = document.getElementById('event-title');
    const eventSubtitle = document.getElementById('event-subtitle');
    const eventIcon = document.querySelector('.event-icon');
    const statusDot = document.querySelector('.status-dot');

    // ── State ─────────────────────────────────────────────────
    let ws = null;
    let typewriterTimeout = null;
    let speechHideTimeout = null;
    let eventHideTimeout = null;
    let messageCount = 0;

    // ── User color palette ────────────────────────────────────
    const USER_COLORS = [
        '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#1abc9c',
        '#3498db', '#9b59b6', '#e91e63', '#00bcd4', '#ff7043',
        '#66bb6a', '#ab47bc', '#5c6bc0', '#26a69a', '#ef5350',
    ];

    function getUserColor(username) {
        let hash = 0;
        for (let i = 0; i < username.length; i++) {
            hash = username.charCodeAt(i) + ((hash << 5) - hash);
        }
        return USER_COLORS[Math.abs(hash) % USER_COLORS.length];
    }

    // ── WebSocket ─────────────────────────────────────────────
    function connect() {
        try {
            ws = new WebSocket(CONFIG.wsUrl);

            ws.onopen = function () {
                console.log('[Overlay] Conectado ao server');
                statusDot.className = 'status-dot connected';
            };

            ws.onclose = function () {
                console.log('[Overlay] Desconectado, reconectando...');
                statusDot.className = 'status-dot disconnected';
                setTimeout(connect, CONFIG.reconnectInterval);
            };

            ws.onerror = function (err) {
                console.error('[Overlay] Erro:', err);
                ws.close();
            };

            ws.onmessage = function (event) {
                try {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    console.error('[Overlay] Erro ao parsear msg:', e);
                }
            };
        } catch (e) {
            console.error('[Overlay] Erro ao conectar:', e);
            setTimeout(connect, CONFIG.reconnectInterval);
        }
    }

    // ── Message Router ────────────────────────────────────────
    function handleMessage(data) {
        switch (data.type) {
            case 'chat':
                addChatMessage(data.username, data.message, data.color);
                break;
            case 'avatar_speech':
                showAvatarSpeech(data.text);
                break;
            case 'avatar_speech_end':
                hideAvatarSpeech();
                break;
            case 'event':
                showEvent(data.event_type, data);
                break;
            case 'topic':
                showTopic(data.text);
                break;
            case 'connected':
                console.log('[Overlay] Server:', data.message);
                break;
            default:
                console.log('[Overlay] Tipo desconhecido:', data.type);
        }
    }

    // ── Chat Messages ─────────────────────────────────────────
    function addChatMessage(username, message, color) {
        const bubble = document.createElement('div');
        bubble.className = 'chat-message';
        messageCount++;

        // Cor custom do user ou gerar baseada no nome
        const userColor = color || getUserColor(username);
        bubble.style.setProperty('--user-color', userColor);
        bubble.querySelector?.('::before')?.style?.setProperty('background', userColor);

        // Aplica cor na borda esquerda via style inline (::before não funciona com data-attr)
        bubble.innerHTML = `
            <span class="chat-username" style="color: ${userColor}">${escapeHtml(username)}</span>
            <span class="chat-text">${escapeHtml(message)}</span>
        `;

        // Aplica a cor na barra lateral via pseudo-element override
        bubble.style.borderLeft = `3px solid ${userColor}`;

        chatMessages.appendChild(bubble);

        // Scroll para baixo
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Remove mensagens antigas se exceder limite
        while (chatMessages.children.length > CONFIG.maxChatMessages) {
            const oldest = chatMessages.children[0];
            oldest.classList.add('fading');
            setTimeout(() => oldest.remove(), 600);
        }

        // Auto-fade após timeout
        setTimeout(() => {
            if (bubble.parentNode) {
                bubble.classList.add('fading');
                setTimeout(() => {
                    if (bubble.parentNode) bubble.remove();
                }, 600);
            }
        }, CONFIG.chatFadeAfterMs);
    }

    // ── Avatar Speech ─────────────────────────────────────────
    function showAvatarSpeech(text) {
        // Limpa timeouts anteriores
        if (typewriterTimeout) clearTimeout(typewriterTimeout);
        if (speechHideTimeout) clearTimeout(speechHideTimeout);

        // Mostra a speech box
        speechBox.classList.remove('hidden');
        speechText.innerHTML = '';

        // Efeito typewriter
        typewriterEffect(text, 0);
    }

    function typewriterEffect(text, index) {
        if (index <= text.length) {
            speechText.innerHTML = escapeHtml(text.substring(0, index)) + '<span class="cursor"></span>';

            typewriterTimeout = setTimeout(() => {
                typewriterEffect(text, index + 1);
            }, CONFIG.speechTypeSpeed);
        } else {
            // Remove cursor quando terminar
            speechText.innerHTML = escapeHtml(text);

            // Auto-hide após um tempo proporcional ao texto
            const displayTime = Math.max(3000, text.length * 80);
            speechHideTimeout = setTimeout(() => {
                hideAvatarSpeech();
            }, displayTime);
        }
    }

    function hideAvatarSpeech() {
        if (typewriterTimeout) clearTimeout(typewriterTimeout);
        if (speechHideTimeout) clearTimeout(speechHideTimeout);
        speechBox.classList.add('hidden');
    }

    // ── Event Alerts ──────────────────────────────────────────
    function showEvent(eventType, data) {
        if (eventHideTimeout) clearTimeout(eventHideTimeout);

        const events = {
            follow: { icon: '💖', title: `${data.username} seguiu!`, subtitle: 'Novo seguidor' },
            sub: { icon: '⭐', title: `${data.username} inscreveu!`, subtitle: data.tier || 'Nova inscrição' },
            bits: { icon: '💎', title: `${data.username} enviou ${data.amount || ''} bits!`, subtitle: 'Obrigado!' },
            raid: { icon: '🎉', title: `Raid de ${data.username}!`, subtitle: `${data.viewers || ''} viewers` },
            gift: { icon: '🎁', title: `${data.username} presenteou sub!`, subtitle: data.recipient || '' },
        };

        const info = events[eventType] || { icon: '✨', title: eventType, subtitle: '' };

        eventIcon.textContent = info.icon;
        eventTitle.textContent = info.title;
        eventSubtitle.textContent = info.subtitle;

        // Mostra com animação
        eventAlert.classList.remove('hidden');

        // Auto-hide
        eventHideTimeout = setTimeout(() => {
            eventAlert.classList.add('hidden');
        }, CONFIG.eventDisplayMs);
    }

    // ── Topic ─────────────────────────────────────────────────
    function showTopic(text) {
        topicText.textContent = text;
        topicBar.classList.remove('hidden');
    }

    // ── Utilities ─────────────────────────────────────────────
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ── Initialize ────────────────────────────────────────────
    connect();

})();
