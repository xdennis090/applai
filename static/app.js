function previewImage(event) {
    const input = event.target;
    const preview = document.getElementById('image-preview');
    const fileNameSpan = document.getElementById('file-name');

    if (input.files && input.files[0]) {
        const reader = new FileReader();

        reader.onload = function(e) {
            preview.src = e.target.result;
        }

        reader.readAsDataURL(input.files[0]);
        fileNameSpan.textContent = input.files[0].name;
    }
}

const statusBar = (message, type = 'info') => {
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.classList.add('visible'));
    setTimeout(() => {
        el.classList.remove('visible');
        setTimeout(() => el.remove(), 400);
    }, 2500);
};

const getCsrfToken = () => {
    const match = document.cookie.split(';').map((c) => c.trim()).find((c) => c.startsWith('csrftoken='));
    if (match) {
        return decodeURIComponent(match.split('=')[1]);
    }
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
};

const api = async (path, { method = 'GET', body } = {}) => {
    const normalizedMethod = method.toUpperCase();
    const options = { method: normalizedMethod, headers: {}, credentials: 'include' };
    if (body && !(body instanceof FormData)) {
        options.body = JSON.stringify(body);
        options.headers['Content-Type'] = 'application/json';
    } else if (body) {
        options.body = body;
    }

    const csrfSafeMethods = ['GET', 'HEAD', 'OPTIONS', 'TRACE'];
    if (!csrfSafeMethods.includes(normalizedMethod)) {
        let token = getCsrfToken();
        if (!token) {
            try {
                await fetch('/api/session/', { credentials: 'include' });
            } catch (e) {
            }
            token = getCsrfToken();
        }
        if (token) {
            options.headers['X-CSRFToken'] = token;
        }
    }

    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || 'Anfrage fehlgeschlagen');
    }
    return data;
};

const listToString = (value) => (Array.isArray(value) ? value.join(', ') : '');
const stringToList = (value) =>
    value
        .split(',')
        .map((entry) => entry.trim())
        .filter(Boolean);
const formatDate = (value) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('de-DE');
};
const formatBytes = (bytes) => {
    if (!bytes || Number.isNaN(bytes)) return '';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
    }
    return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
};

const authPanel = document.getElementById('auth-panel');
const authOverlay = document.getElementById('auth-overlay');
const navOverlay = document.getElementById('nav-overlay');
const burgerButton = document.getElementById('burger');
const sessionInfoEl = document.getElementById('session-info');
const loginTrigger = document.getElementById('open-auth');
const profileMenu = document.getElementById('profile-menu');
const profileTrigger = document.getElementById('profile-trigger');
const profileDropdown = document.getElementById('profile-dropdown');
const profileLogoutBtn = document.getElementById('profile-logout');
const profileAdminLink = document.getElementById('profile-admin');
const profileSettingsBtn = document.querySelector('[data-profile-action="settings"]');
const profileAvatar = document.getElementById('profile-avatar');
const assistantEditor = document.getElementById('assistant-editor');
const assistantMeta = document.getElementById('assistant-meta');
const copyEditorBtn = document.getElementById('copy-editor');
const saveDraftBtn = document.getElementById('save-draft');
const applicationListEl = document.getElementById('application-list');
const bookmarkListEl = document.getElementById('bookmark-list');
const photoListEl = document.getElementById('photo-list');
const toneInput = document.getElementById('tone-input');
const structureLinks = document.getElementById('structure-links');
const structureNote = document.getElementById('structure-note');
const structureDetailInput = document.getElementById('structure-detail');
const structureSaveBtn = document.getElementById('structure-save');
const structureInsertContainer = document.getElementById('structure-inserts');
const toneChips = document.getElementById('tone-chips');
const generateBtn = document.querySelector('#assistant-form button[type="submit"]');
const chatSend = document.getElementById('chat-send');
const chatStatus = document.querySelector('.chat-card__meta');
const saveJobBtn = document.getElementById('save-job');
const chatBoxInput = document.getElementById('chat-box-input');
const chatThread = document.getElementById('chat-thread');
const profilePreviewEl = document.getElementById('profile-preview');
const adminLink = document.getElementById('admin-link');
const ollamaScanBtn = document.getElementById('ollama-scan');
const ollamaModelsContainer = document.getElementById('ollama-models');
const ollamaStatus = document.getElementById('ollama-status');
const ollamaSelectedLabel = document.getElementById('ollama-selected');
const comfyScanBtn = document.getElementById('comfy-scan');
const comfyModelsContainer = document.getElementById('comfy-models');
const comfyStatus = document.getElementById('comfy-status');
const comfySelectedLabel = document.getElementById('comfy-selected');
const photoForm = document.getElementById('photo-upload-form');
const photoFileInput = document.getElementById('photo-file');
const photoFileName = document.getElementById('photo-file-name');
const photoPreviewInput = document.getElementById('photo-preview-input');
const photoPreviewOutput = document.getElementById('photo-preview-output');
const photoOutputPlaceholder = document.getElementById('photo-output-placeholder');
const photoOutputFrame = document.getElementById('photo-output-frame');
const photoCheckpointSelect = document.getElementById('photo-checkpoint');
const photoSubmitBtn = document.getElementById('photo-submit');
const refreshPhotoHistoryBtn = document.getElementById('refresh-photo-history');
const photoHistoryGrid = document.getElementById('photo-history-grid');
const pages = document.querySelectorAll('.page');
const pageLinks = document.querySelectorAll('[data-page-link]');
const collapseButtons = document.querySelectorAll('[data-collapse-toggle]');
const collapseState = JSON.parse(localStorage.getItem('applai_collapse') || '{}');
const editorButtons = document.querySelectorAll('.editor-btn');
const loadBookmarksBtn = document.getElementById('load-bookmarks');
const loadApplicationsBtn = document.getElementById('load-applications');
const loadPhotosBtn = document.getElementById('load-photos');
const structureContentDisplay = document.getElementById('structure-content-display');
const structureLockCheckbox = document.getElementById('structure-lock');
const historyStack = [];
const redoStack = []; 
const undoBtn = document.getElementById('undo-btn');
const redoBtn = document.getElementById('redo-btn');

const COMFY_CHECKPOINT_KEY = 'applai_comfy_checkpoint';

function debounce(func, timeout = 500) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, timeout);
    };
}

const cleanHTMLForTextarea = (html) => {
    if (!html) return '';
    return html
        .replace(/<br\s*\/?>/gi, '\n') 
        .replace(/<\/p>/gi, '\n')      
        .replace(/<[^>]+>/g, '');    
};


const syncEditorToStructure = () => {
    if (!assistantEditor) return;

    const fullText = cleanHTMLForTextarea(assistantEditor.innerHTML);
    const lines = fullText.split('\n');

    if (lines.length < 2) return;

    let introCut = 0;
    for (let i = 0; i < lines.length; i++) {
        if (lines[i].toLowerCase().includes('sehr geehrte')) {
            let j = i + 1;
            while (j < lines.length && lines[j].trim() === '') j++;
            while (j < lines.length && lines[j].trim() !== '') j++;
            introCut = j;
            break;
        }
    }

    let outroCut = lines.length;
    const greetingMarkers = ['mit freundlichen', 'freundliche grüße', 'hochachtungsvoll', 'beste grüße', 'viele grüße'];
    const ctaMarkers = ['freue mich', 'vielen dank', 'für ein persönliches', 'gehaltsvorstellung', 'eintrittstermin'];

    let greetingIndex = -1;
    for (let i = lines.length - 1; i >= 0; i--) {
        if (greetingMarkers.some(m => lines[i].toLowerCase().includes(m))) {
            greetingIndex = i;
            break;
        }
    }

    if (greetingIndex !== -1) {
        outroCut = greetingIndex;
        let k = greetingIndex - 1;
        while (k > introCut && lines[k].trim() === '') k--;
        if (k > introCut && ctaMarkers.some(m => lines[k].toLowerCase().includes(m))) {
            while (k > introCut && lines[k].trim() !== '') k--;
            outroCut = k + 1;
        }
    }

    const introPart = lines.slice(0, introCut).join('\n').trim();
    const bodyPart = lines.slice(introCut, outroCut).join('\n').trim();
    const outroPart = lines.slice(outroCut).join('\n').trim();

    if (!structureLocks.Einleitung) structureContent.Einleitung = introPart;
    if (!structureLocks.Hauptteil) structureContent.Hauptteil = bodyPart;
    if (!structureLocks.Schluss) structureContent.Schluss = outroPart;

    updateStructureUI();
};

const pushEditorHistoryIfChanged = debounce(() => {
    const lastState = historyStack[historyStack.length - 1];
    const currentHTML = assistantEditor ? assistantEditor.innerHTML : '';
    
    if (!lastState || lastState.editorHTML !== currentHTML) {
        pushToHistory();
    }
}, 800); 

if (assistantEditor) {
    assistantEditor.addEventListener('input', () => {
        pushEditorHistoryIfChanged(); 
        syncEditorToStructure();     
    });
}

const getCaretCharacterOffsetWithin = (element) => {
    let caretOffset = 0;
    const doc = element.ownerDocument || element.getOwnerDocument();
    const win = doc.defaultView || doc.parentWindow;
    const sel = win.getSelection();
    if (sel.rangeCount > 0) {
        const range = sel.getRangeAt(0);
        const preCaretRange = range.cloneRange();
        preCaretRange.selectNodeContents(element);
        preCaretRange.setEnd(range.endContainer, range.endOffset);
        caretOffset = preCaretRange.toString().length;
    }
    return caretOffset;
};

const setCaretPosition = (element, offset) => {
    const range = document.createRange();
    const sel = window.getSelection();
    let charCount = 0;
    let stop = false;

    const traverseNodes = (node) => {
        if (stop) return;
        if (node.nodeType === 3) {
            const nextCharCount = charCount + node.length;
            if (!stop && offset <= nextCharCount) {
                range.setStart(node, offset - charCount);
                range.collapse(true);
                stop = true;
            }
            charCount = nextCharCount;
        } else {
            for (let i = 0; i < node.childNodes.length; i++) {
                traverseNodes(node.childNodes[i]);
            }
        }
    };

    traverseNodes(element);
    sel.removeAllRanges();
    sel.addRange(range);
};


const captureState = () => {
    return {
        content: { ...structureContent },
        locks: { ...structureLocks },
        prompts: { ...structurePrompts }, 
        editorHTML: assistantEditor ? assistantEditor.innerHTML : '',
        metaText: assistantMeta ? assistantMeta.textContent : '',
        caretOffset: assistantEditor ? getCaretCharacterOffsetWithin(assistantEditor) : 0
    };
};

const applyState = (state) => {
    if (!state) return;
    
    Object.assign(structureContent, state.content);
    Object.assign(structureLocks, state.locks);
    Object.assign(structurePrompts, state.prompts);

    if (assistantEditor) {
        assistantEditor.innerHTML = state.editorHTML;
        assistantEditor.focus();
        if (state.caretOffset > 0) {
            setCaretPosition(assistantEditor, state.caretOffset);
        }
    }
    
    if (assistantMeta) assistantMeta.textContent = state.metaText;
    updateStructureUI();
};

const isSameState = (s1, s2) => {
    if (!s1 || !s2) return false;
    return s1.editorHTML === s2.editorHTML && 
           JSON.stringify(s1.content) === JSON.stringify(s2.content);
};

const pushToHistory = () => {
    const currentState = captureState();
    
    if (historyStack.length > 0) {
        const lastState = historyStack[historyStack.length - 1];
        if (isSameState(lastState, currentState)) {
            return; 
        }
    }

    if (historyStack.length > 40) historyStack.shift(); 
    
    historyStack.push(currentState);
    redoStack.length = 0; 
    updateHistoryButtons();
};

const performUndo = () => {
    if (historyStack.length === 0) return;

    const currentState = captureState();
    const lastSavedState = historyStack[historyStack.length - 1];

    if (isSameState(currentState, lastSavedState)) {
        if (historyStack.length <= 1) return; 
        redoStack.push(historyStack.pop());
    } else {
        redoStack.push(currentState);
    }

    const previousState = historyStack[historyStack.length - 1];
    applyState(previousState);

    updateHistoryButtons();
    statusBar('Rückgängig gemacht', 'info');
};

const performRedo = () => {
    if (redoStack.length === 0) return;

    const currentState = captureState();
    historyStack.push(currentState);

    const futureState = redoStack.pop();
    applyState(futureState);

    updateHistoryButtons();
    statusBar('Wiederhergestellt', 'info');
};

const updateHistoryButtons = () => {
    if (undoBtn) {
        undoBtn.disabled = historyStack.length === 0;
        undoBtn.style.opacity = historyStack.length === 0 ? '0.5' : '1';
    }
    if (redoBtn) {
        redoBtn.disabled = redoStack.length === 0;
        redoBtn.style.opacity = redoStack.length === 0 ? '0.5' : '1';
    }
};

if (undoBtn) undoBtn.addEventListener('click', performUndo);
if (redoBtn) redoBtn.addEventListener('click', performRedo);

document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        performUndo();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        performRedo();
    }
});

let currentStructure = 'Einleitung';
const structurePrompts = {
    Einleitung: '',
    Hauptteil: '',
    Schluss: '',
};

const structureContent = {
    Einleitung: '',
    Hauptteil: '',
    Schluss: '',
};

const structureLocks = {
    Einleitung: false,
    Hauptteil: false,
    Schluss: false,
};

let cachedProfile = null;
let isAuthenticated = false;
const applicationCache = {};
const chatMessages = [];
const OLLAMA_MODEL_KEY = 'applai_ollama_model';
let ollamaReady = false;
const closeNav = () => document.body.classList.remove('nav-open');
const toggleNav = () => document.body.classList.toggle('nav-open');
const closeProfileMenu = () => {
    if (profileMenu) {
        profileMenu.classList.remove('open');
    }
};
const toggleProfileMenu = () => {
    if (profileMenu) {
        profileMenu.classList.toggle('open');
    }
};

if (burgerButton) {
    burgerButton.addEventListener('click', toggleNav);
}
if (navOverlay) {
    navOverlay.addEventListener('click', () => {
        closeNav();
        closeProfileMenu();
    });
}
if (document.getElementById('main-nav')) {
    document.querySelectorAll('#main-nav a').forEach((link) => {
        link.addEventListener('click', closeNav);
    });
}

if (profileTrigger) {
    profileTrigger.addEventListener('click', (event) => {
        event.stopPropagation();
        toggleProfileMenu();
    });
}
document.addEventListener('click', (event) => {
    if (profileMenu && !profileMenu.contains(event.target)) {
        closeProfileMenu();
    }
});

const setPage = (pageName) => {
    if (!pageName) {
        return;
    }
    pages.forEach((section) => {
        section.classList.toggle('active', section.dataset.page === pageName);
    });
    pageLinks.forEach((link) => {
        if (link.dataset.pageLink === pageName) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
    closeNav();
    closeProfileMenu();
    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (pageName === 'archiv') {
        refreshApplications();
        refreshBookmarks();
        refreshPhotos();
    }
};

pageLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
        const targetPage = link.dataset.pageLink;
        if (targetPage) {
            event.preventDefault();
            setPage(targetPage);
            localStorage.setItem('applai_page', targetPage);
        }
    });
});

collapseButtons.forEach((button) => {
    const targetId = button.dataset.collapseToggle;
    const card = document.querySelector(`[data-collapse-id="${targetId}"]`);
    if (!card) return;

    if (collapseState[targetId]) {
        card.classList.add('collapsed');
    }

    const updateState = () => {
        const collapsed = card.classList.contains('collapsed');
        const icon = button.querySelector('svg');
        const label = button.childNodes[button.childNodes.length - 1];
        if (label && label.nodeType === Node.TEXT_NODE) {
            label.textContent = collapsed ? ' ' : ' ';
        }
        if (icon) {
            icon.style.transform = collapsed ? 'rotate(-90deg)' : 'rotate(0deg)';
        }
    };

    button.addEventListener('click', () => {
        card.classList.toggle('collapsed');
        collapseState[targetId] = card.classList.contains('collapsed');
        localStorage.setItem('applai_collapse', JSON.stringify(collapseState));
        updateState();
    });

    updateState();
});

const toggleAuthPanel = (open) => {
    if (!authPanel || !authOverlay) return;
    authPanel.classList.toggle('visible', open);
    authOverlay.classList.toggle('visible', open);
};

const showRegisterBtn = document.getElementById('show-register');
const showLoginBtn = document.getElementById('show-login');

const setAuthMode = (mode = 'login') => {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    if (!loginForm || !registerForm) return;
    loginForm.classList.toggle('active', mode === 'login');
    registerForm.classList.toggle('active', mode === 'register');
};

const openAuthButtons = [loginTrigger].filter(Boolean);
openAuthButtons.forEach((btn) =>
    btn.addEventListener('click', () => {
        closeNav();
        closeProfileMenu();
        setAuthMode('login');
        toggleAuthPanel(true);
    })
);

const closeAuthButton = document.getElementById('close-auth');
if (closeAuthButton) {
    closeAuthButton.addEventListener('click', () => toggleAuthPanel(false));
}
if (authOverlay) {
    authOverlay.addEventListener('click', () => toggleAuthPanel(false));
}

if (showRegisterBtn) {
    showRegisterBtn.addEventListener('click', () => setAuthMode('register'));
}
if (showLoginBtn) {
    showLoginBtn.addEventListener('click', () => setAuthMode('login'));
}

const setButtonLoading = (button, isLoading, label = 'Lädt...') => {
    if (!button) return;
    if (isLoading) {
        button.dataset.originalText = button.dataset.originalText || button.innerHTML; 
        button.disabled = true;
        button.classList.add('is-loading');
        button.innerHTML = `<span class="spinner" aria-hidden="true"></span>${label}`;
    } else {
        button.disabled = false;
        button.classList.remove('is-loading');
        const original = button.dataset.originalText;
        if (original) {
            button.innerHTML = original; 
        }
    }
};

const appendChatNotice = (text) => {
    if (!chatThread || !text) return;
    const existing = chatThread.querySelector('.chat-message.auth-warning');
    if (existing) return;
    if (chatThread.querySelector('.chat-message.system')) {
        chatThread.innerHTML = '';
    }
    const el = document.createElement('div');
    el.className = 'chat-message system auth-warning';
    el.textContent = text;
    chatThread.appendChild(el);
};

const setChatStatus = (state = 'offline') => {
    if (!chatStatus) return;
    const dot = chatStatus.querySelector('.status-dot');
    const label = chatStatus.querySelector('span:last-child');
    const validStates = ['loading', 'ready', 'needs-auth', 'offline', 'error'];
    const nextState = validStates.includes(state) ? state : 'offline';
    dot?.classList.remove('loading', 'ready', 'offline', 'needs-auth', 'error');
    if (nextState === 'loading') {
        dot?.classList.add('loading');
        if (label) label.textContent = 'generiert...';
        return;
    }
    if (nextState === 'ready') {
        dot?.classList.add('ready');
        if (label) label.textContent = 'ready';
        return;
    }
    if (nextState === 'needs-auth') {
        dot?.classList.add('needs-auth');
        if (label) label.textContent = 'Login nötig';
        return;
    }
    if (nextState === 'error') {
        dot?.classList.add('offline');
        if (label) label.textContent = 'Fehler';
        return;
    }
    dot?.classList.add('offline');
    if (label) label.textContent = 'offline';
};

const syncLLMAccessWarnings = () => {
    if (!isAuthenticated) {
        appendChatNotice('Bitte einloggen, um den LLM-Chat zu nutzen.');
    } else if (chatThread) {
        const notice = chatThread.querySelector('.chat-message.auth-warning');
        if (notice) {
            notice.remove();
            if (!chatThread.children.length) {
                const placeholder = document.createElement('div');
                placeholder.className = 'chat-message system';
                placeholder.textContent = 'Noch keine Nachrichten.';
                chatThread.appendChild(placeholder);
            }
        }
    }
    if (generateBtn) {
        generateBtn.disabled = !isAuthenticated;
        generateBtn.title = !isAuthenticated ? 'Login nötig, um den LLM zu nutzen.' : '';
    }
    if (chatSend) {
        chatSend.disabled = !isAuthenticated;
        chatSend.title = !isAuthenticated ? 'Login nötig, um den LLM zu nutzen.' : '';
    }
    if (!ollamaReady) {
        setChatStatus(isAuthenticated ? 'offline' : 'needs-auth');
    } else {
        setChatStatus(isAuthenticated ? 'ready' : 'needs-auth');
    }
};

const updateSessionUI = (user) => {
    isAuthenticated = Boolean(user);
    const hasUser = Boolean(user);
    if (sessionInfoEl) {
        sessionInfoEl.textContent = hasUser ? user.username : '';
    }
    if (profileAvatar) {
        const initial = hasUser && user.username ? user.username.trim().charAt(0).toUpperCase() : '👤';
        profileAvatar.textContent = initial || '👤';
    }
    if (profileMenu) {
        profileMenu.classList.toggle('hidden', !hasUser);
        if (!hasUser) {
            profileMenu.classList.remove('open');
        }
    }
    if (loginTrigger) {
        loginTrigger.classList.toggle('hidden', hasUser);
    }
    if (profileAdminLink) {
        const showAdmin = hasUser && (user.is_staff || user.is_superuser);
        profileAdminLink.classList.toggle('hidden', !showAdmin);
    }
    if (saveDraftBtn) {
        saveDraftBtn.disabled = !hasUser;
        saveDraftBtn.title = hasUser ? '' : 'Bitte einloggen, um Entwürfe zu speichern.';
    }
    syncLLMAccessWarnings();
};

if (profileLogoutBtn) {
    profileLogoutBtn.addEventListener('click', async () => {
        try {
            await api('/api/logout/', { method: 'POST' });
        } catch (error) {
        } finally {
            cachedProfile = null;
            updateSessionUI(null);
            closeProfileMenu();
            const profileFormEl = document.getElementById('profile-form');
            if (profileFormEl) {
                profileFormEl.reset();
            }
            if (assistantEditor) {
                assistantEditor.innerHTML = '';
            }
            if (profilePreviewEl) {
                profilePreviewEl.classList.remove('active');
            }
            Object.keys(structureContent).forEach(k => structureContent[k] = '');
            updateStructureUI();
        }
    });
}

if (profileSettingsBtn) {
    profileSettingsBtn.addEventListener('click', () => {
        closeProfileMenu();
        setPage('settings');
        localStorage.setItem('applai_page', 'settings');
    });
}

const fetchSession = async () => {
    try {
        const data = await api('/api/session/');
        updateSessionUI(data.user);
        cachedProfile = data.user?.profile || null;
        renderProfile(cachedProfile);
        if (data.user) {
            refreshApplications();
            refreshBookmarks();
        }
        syncLLMAccessWarnings();
    } catch (error) {
        if (profilePreviewEl) {
            profilePreviewEl.classList.remove('active');
        }
        syncLLMAccessWarnings();
    }
};

const loginForm = document.getElementById('login-form');
loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    try {
        const data = await api('/api/login/', {
            method: 'POST',
            body: Object.fromEntries(formData.entries()),
        });
        statusBar('Login erfolgreich', 'success');
        toggleAuthPanel(false);
        updateSessionUI(data.user);
        cachedProfile = data.user.profile;
        renderProfile(cachedProfile);
        refreshApplications();
        syncLLMAccessWarnings();
    } catch (error) {
        statusBar(error.message, 'error');
    }
});

const registerForm = document.getElementById('register-form');
registerForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(registerForm);
    try {
        const data = await api('/api/register/', {
            method: 'POST',
            body: Object.fromEntries(formData.entries()),
        });
        statusBar('Account erstellt und eingeloggt', 'success');
        toggleAuthPanel(false);
        updateSessionUI(data.user);
        cachedProfile = data.user.profile;
        renderProfile(cachedProfile);
        refreshApplications();
        syncLLMAccessWarnings();
    } catch (error) {
        statusBar(error.message, 'error');
    }
});

const renderProfile = (profile) => {
    if (!profile) {
        const form = document.getElementById('profile-form');
        if (form) {
            form.reset();
        }
        renderStructureInserts(null);
        return;
    }

    const form = document.getElementById('profile-form');
    if (form && profile) {
        form.contact_email.value = profile.contact_email || '';
        form.phone.value = profile.phone || '';
        form.location.value = profile.location || '';
        form.education.value = profile.education || '';
        form.experience.value = profile.experience || '';
        form.resume_text.value = profile.resume_text || '';
        form.skills.value = listToString(profile.skills);
        form.soft_skills.value = listToString(profile.soft_skills);
        form.hobbies.value = listToString(profile.hobbies);
    }

    if (profilePreviewEl) {
        profilePreviewEl.innerHTML = `
            <strong>Letzte Aktualisierung</strong><br>
            Skills: ${listToString(profile.skills)}<br>
            Bewerbungen: ${profile.applications.length} | Foto-Sessions: ${profile.photo_sessions.length}
        `;
        profilePreviewEl.classList.add('active');
    }
    renderStructureInserts(profile);
};

const loadProfileBtn = document.getElementById('load-profile');
if (loadProfileBtn) {
    loadProfileBtn.addEventListener('click', async () => {
        try {
            const data = await api('/api/profile/');
            cachedProfile = data.profile;
            renderProfile(cachedProfile);
            statusBar('Profil geladen', 'success');
        } catch (error) {
            statusBar('Bitte zuerst einloggen', 'error');
        }
    });
}

const profileForm = document.getElementById('profile-form');
if (profileForm) {
    profileForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(profileForm);
        const payload = Object.fromEntries(formData.entries());
        payload.skills = stringToList(payload.skills);
        payload.soft_skills = stringToList(payload.soft_skills);
        payload.hobbies = stringToList(payload.hobbies);

        try {
            const data = await api('/api/profile/', { method: 'POST', body: payload });
            cachedProfile = data.profile;
            renderProfile(cachedProfile);
            statusBar('Profil gespeichert', 'success');
        } catch (error) {
            statusBar(error.message, 'error');
        }
    });
}

const updateStructureUI = () => {
    if (structureDetailInput) {
        structureDetailInput.value = structurePrompts[currentStructure] || '';
    }
    
    if (structureContentDisplay) {
        structureContentDisplay.value = structureContent[currentStructure] || '';
        
        const isLocked = structureLocks[currentStructure] || false;
        structureContentDisplay.disabled = isLocked;
        
        if (isLocked) {
            structureContentDisplay.style.backgroundColor = '#f3f4f6';
            structureContentDisplay.style.color = '#6b7280'; 
            structureContentDisplay.style.cursor = 'not-allowed';
        } else {
            structureContentDisplay.style.backgroundColor = '';
            structureContentDisplay.style.color = '';
            structureContentDisplay.style.cursor = '';
        }
    }
    
    if (structureLockCheckbox) {
        structureLockCheckbox.checked = structureLocks[currentStructure] || false;
    }
};

const structureHints = {
    Einleitung: 'Fokus: Einleitung – persönlicher Einstieg & Bezug zur Firma.',
    Hauptteil: 'Fokus: Hauptteil – relevante Skills + Projekte beschreiben.',
    Schluss: 'Fokus: Schluss – Dank, Motivation und Call-to-Action.',
};

if (structureLinks && structureNote) {
    structureLinks.addEventListener('click', (event) => {
        if (event.target.matches('button[data-structure]')) {
            const value = event.target.dataset.structure;
            currentStructure = value;
            structureLinks.querySelectorAll('button').forEach((btn) => btn.classList.remove('active'));
            event.target.classList.add('active');
            structureNote.textContent = structureHints[value] || value;
            updateStructureUI(); 
        }
    });
    updateStructureUI(); 
}

if (structureSaveBtn && structureDetailInput) {
    structureSaveBtn.addEventListener('click', () => {
        structurePrompts[currentStructure] = structureDetailInput.value.trim();
        statusBar(`Verfeinerung für ${currentStructure} aktualisiert`, 'success');
    });
}

if (structureContentDisplay) {
    structureContentDisplay.addEventListener('input', (e) => {
        structureContent[currentStructure] = e.target.value;
    });
}

if (structureLockCheckbox) {
    structureLockCheckbox.addEventListener('change', (e) => {
        structureLocks[currentStructure] = e.target.checked;
        
        updateStructureUI(); 

        if (e.target.checked) {
            statusBar(`${currentStructure} gesperrt `, 'info');
        } else {
            statusBar(`${currentStructure} entsperrt `, 'info');
        }
    });
}

const renderStructureInserts = (profile) => {
    if (!structureInsertContainer) return;
    structureInsertContainer.innerHTML = '';
    const chips = [];
    if (profile?.hobbies?.length) {
        profile.hobbies.forEach((hobby) => {
            chips.push({
                label: `Hobby: ${hobby}`,
                text: `Bitte integriere mein Hobby ${hobby} in diesen Abschnitt.`,
            });
        });
    }
    if (profile?.skills?.length) {
        profile.skills.forEach((skill) => {
            chips.push({
                label: `Skill: ${skill}`,
                text: `Betone meine Fähigkeit ${skill} hier besonders.`,
            });
        });
    }
    if (!chips.length) {
        const msg = document.createElement('p');
        msg.className = 'muted';
        msg.textContent = 'Profil laden, um Hobbys oder Skills als Unterprompt hinzufügen zu können.';
        structureInsertContainer.appendChild(msg);
        return;
    }
    const label = document.createElement('span');
    label.className = 'muted';
    label.textContent = 'Hinzufügen:';
    structureInsertContainer.appendChild(label);
    chips.forEach((chip) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'insert-chip';
        button.dataset.insert = chip.text;
        button.textContent = chip.label;
        structureInsertContainer.appendChild(button);
    });
};

const insertIntoStructureDetail = (text) => {
    if (!structureDetailInput) return;
    const current = structureDetailInput.value;
    structureDetailInput.value = current ? `${current}\n${text}` : text;
    structureDetailInput.focus();
};

if (structureInsertContainer) {
    structureInsertContainer.addEventListener('click', (event) => {
        if (event.target.matches('.insert-chip')) {
            insertIntoStructureDetail(event.target.dataset.insert || '');
        }
    });
}

if (toneChips && toneInput) {
    toneChips.addEventListener('click', (event) => {
        if (event.target.matches('button[data-tone]')) {
            toneChips.querySelectorAll('button').forEach((btn) => btn.classList.remove('active'));
            event.target.classList.add('active');
            toneInput.value = event.target.dataset.tone;
        }
    });
}

const assistantForm = document.getElementById('assistant-form');
    if (assistantForm) {
        assistantForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (!isAuthenticated) {
                statusBar('Bitte zuerst einloggen, um den Generator zu nutzen.', 'error');
                syncLLMAccessWarnings();
                return;
            }
        const payload = Object.fromEntries(new FormData(assistantForm).entries());
        payload.structure_details = structurePrompts;
        const selectedModel = localStorage.getItem(OLLAMA_MODEL_KEY) || null;
        payload.model = selectedModel || undefined; 
        
        if (structureLocks.Einleitung) {
            payload.locked_intro = structureContent.Einleitung;
        }
        if (structureLocks.Hauptteil) {
            payload.locked_body = structureContent.Hauptteil;
        }
        if (structureLocks.Schluss) {
            payload.locked_outro = structureContent.Schluss;
        }

            try {
                pushToHistory();
                setButtonLoading(generateBtn, true, 'Generiere...');
                const data = await api('/api/assistant/generate/', { method: 'POST', body: payload });

                if (data.application && data.application.id) {
                    currentDraftId = data.application.id;
                }

                if (assistantEditor) {
                    assistantEditor.innerHTML = data.generated.cover_letter.replace(/\n/g, '<br>');
                }

                if (data.generated.structure) {
                    structureContent.Einleitung = cleanHTMLForTextarea(data.generated.structure.Einleitung);
                    structureContent.Hauptteil = cleanHTMLForTextarea(data.generated.structure.Hauptteil);
                    structureContent.Schluss = cleanHTMLForTextarea(data.generated.structure.Schluss);
                    updateStructureUI();
                }

                if (structureContent.Hauptteil.includes('Mit freundlichen Grüßen') || structureContent.Hauptteil.includes('Für ein persönliches Gespräch')) {
                    const schlussTrigger = ['Für ein persönliches', 'Ich würde mich freuen', 'Mit freundlichen'];
                    let text = structureContent.Hauptteil;
                    let splitIndex = -1;

                    for (const trigger of schlussTrigger) {
                        const index = text.lastIndexOf(trigger);
                        if (index !== -1 && (splitIndex === -1 || index < splitIndex)) {
                            splitIndex = index;
                        }
                    }

                    if (splitIndex !== -1) {
                        const neuerHauptteil = text.substring(0, splitIndex).trim();
                        const extraSchluss = text.substring(splitIndex).trim();
                        
                        structureContent.Hauptteil = neuerHauptteil;
                        structureContent.Schluss = extraSchluss + '\n\n' + structureContent.Schluss;
                    }
                }

                updateStructureUI();

                pushToHistory(); 

                if (assistantEditor) assistantEditor.focus();
                statusBar('Anschreiben erstellt', 'success');
            } catch (error) {
                statusBar(error.message, 'error');
            } finally {
                setButtonLoading(generateBtn, false);
            }
        });
    }

const bookmarkFromForm = async () => {
    const formData = new FormData(assistantForm);
    const job = {
        title: formData.get('job_title') || 'Unbenannt',
        company: formData.get('company') || '',
        location: '',
        description: formData.get('job_description') || '',
        link: formData.get('job_link') || '',
        match: { score: 0, summary: 'Manuell gespeichert' },
    };
    if (!job.title.trim()) {
        statusBar('Bitte Jobtitel eintragen.', 'error');
        return;
    }
    try {
        await api('/api/jobs/bookmarks/', {
            method: 'POST',
            body: {
                title: job.title,
                company: job.company,
                location: job.location,
                description: job.description,
                link: job.link,
                match: job.match,
            },
        });
        statusBar('Job gespeichert', 'success');
        await refreshBookmarks();
    } catch (error) {
        statusBar(error.message, 'error');
    }
};

if (saveJobBtn) {
    saveJobBtn.addEventListener('click', bookmarkFromForm);
}

if (copyEditorBtn && assistantEditor) {
    copyEditorBtn.addEventListener('click', async () => {
        const text = assistantEditor.innerText.trim();
        if (!text) {
            statusBar('Kein Text zum Kopieren vorhanden.', 'error');
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            statusBar('Anschreiben kopiert', 'success');
        } catch (error) {
            statusBar('Kopieren nicht möglich', 'error');
        }
    });
}

const saveDraft = async () => {
    if (!isAuthenticated) {
        statusBar('Bitte zuerst einloggen.', 'error');
        return;
    }
    const html = assistantEditor?.innerHTML.trim();
    if (!html) {
        statusBar('Kein Entwurf vorhanden.', 'error');
        return;
    }
    const formData = assistantForm ? new FormData(assistantForm) : null;
    const jobTitle = formData?.get('job_title') || 'Entwurf';
    const company = formData?.get('company') || '';
    const description = formData?.get('job_description') || '';
    const tone = toneInput?.value || 'formal';
    const focusPoints = Object.entries(structurePrompts)
        .filter(([, value]) => value)
        .map(([section]) => section);
    try {
        await api('/api/assistant/save/', {
            method: 'POST',
            body: {
                job_title: jobTitle,
                company,
                job_description,
                tone,
                focus_points: focusPoints,
                cover_letter: html,
                match_notes: 'Manuell gespeichert',
                section_intro: structureContent.Einleitung,
                section_body: structureContent.Hauptteil,
                section_outro: structureContent.Schluss
            },
        });
        statusBar('Entwurf gespeichert', 'success');
        await refreshApplications();
    } catch (error) {
        statusBar(error.message, 'error');
    }
};

if (saveDraftBtn) {
    saveDraftBtn.addEventListener('click', saveDraft);
}

editorButtons.forEach((button) => {
    button.addEventListener('click', () => {
        const command = button.dataset.command;
        if (!command || !assistantEditor) return;
        pushToHistory();
        assistantEditor.focus();
        document.execCommand(command, false, null);
    });
});

const renderList = (el, items, formatter, emptyText) => {
    if (!el) return;
    el.innerHTML = '';
    if (!items.length) {
        const li = document.createElement('li');
        li.className = 'archive-empty';
        li.textContent = emptyText;
        el.appendChild(li);
        return;
    }
    items.forEach((item) => {
        const li = document.createElement('li');
        li.innerHTML = formatter(item);
        el.appendChild(li);
    });
};

const appendChatMessage = (role, content) => {
    if (!chatThread) return;
    if (chatThread.querySelector('.chat-message.system')) {
        chatThread.innerHTML = '';
    }
    const el = document.createElement('div');
    el.className = `chat-message ${role}`;
    el.textContent = content;
    chatThread.appendChild(el);
    chatThread.scrollTop = chatThread.scrollHeight;
};

const refreshApplications = async () => {
    try {
        const data = await api('/api/assistant/history/');
        applicationListEl.innerHTML = '';
        if (!data.applications.length) {
            const empty = document.createElement('li');
            empty.className = 'archive-empty';
            empty.textContent = 'Keine Anschreiben gespeichert.';
            applicationListEl.appendChild(empty);
            return;
        }
        data.applications.forEach((app) => {
            applicationCache[app.id] = app;
            const li = document.createElement('li');
            li.innerHTML = `<strong>${app.job_title}</strong> – ${app.company || ''}<br><small>${app.match_notes || ''}</small>`;
            const actions = document.createElement('div');
            actions.className = 'archive-actions';
            const loadBtn = document.createElement('button');
            loadBtn.type = 'button';
            loadBtn.className = 'ghost';
            loadBtn.textContent = 'Laden';
            loadBtn.dataset.appId = app.id;
            loadBtn.dataset.action = 'load';
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'ghost danger';
            deleteBtn.textContent = 'Löschen';
            deleteBtn.dataset.appId = app.id;
            deleteBtn.dataset.action = 'delete';
            actions.appendChild(loadBtn);
            actions.appendChild(deleteBtn);
            li.appendChild(actions);
            applicationListEl.appendChild(li);
        });
    } catch (error) {
        statusBar('Keine Berechtigung: bitte einloggen.', 'error');
    }
};

const ensureApplicationsLoaded = () => {
    if (applicationListEl && !applicationListEl.children.length) {
        refreshApplications();
    }
};

const refreshBookmarks = async () => {
    try {
        const data = await api('/api/jobs/bookmarks/');

        bookmarkListEl.innerHTML = '';

        if (!data.bookmarks || !data.bookmarks.length) {
            const empty = document.createElement('li');
            empty.className = 'archive-empty';
            empty.textContent = 'Keine Jobs gespeichert.';
            bookmarkListEl.appendChild(empty);
            return;
        }

        data.bookmarks.forEach(job => {
            applicationCache['job_' + job.id] = job;

            const li = document.createElement('li');

            const shortDesc = (job.description || '').length > 35
                ? (job.description || '').substring(0, 35) + '...'
                : (job.description || '');

            li.innerHTML = `<strong>${job.title}</strong> – ${job.company || ''}<br><small>${shortDesc}</small>`;

            const actions = document.createElement('div');
            actions.className = 'archive-actions';

            const loadBtn = document.createElement('button');
            loadBtn.type = 'button';
            loadBtn.className = 'ghost';
            loadBtn.textContent = 'Laden';
            loadBtn.dataset.jobId = job.id;
            loadBtn.dataset.action = 'load';

            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'ghost danger';
            deleteBtn.textContent = 'Löschen';
            deleteBtn.dataset.jobId = job.id;
            deleteBtn.dataset.action = 'delete';

            actions.appendChild(loadBtn);
            actions.appendChild(deleteBtn);
            li.appendChild(actions);
            bookmarkListEl.appendChild(li);
        });

    } catch (error) {
        statusBar('Keine Berechtigung: bitte einloggen.', 'error');
    }
};

const refreshPhotos = async () => {
    if (!photoListEl) return;

    try {
        const data = await api('/api/photos/history/');
        const sessions = data.photo_sessions || [];

        renderList(
            photoListEl,
            sessions,
            (session) => {
                const imgSrc = session.result_image || session.source_image || '';
                const dateStr = session.created_at ? session.created_at.slice(0, 16).replace('T', ' ') : '';
                const styleLabel = (session.adjustments && session.adjustments.style) ? session.adjustments.style : 'Standard';

                return `
                    <div style="display: flex; align-items: center; gap: 12px;">
                        ${imgSrc ?
                            `<img src="${imgSrc}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0;" alt="Foto">`
                            : '<div style="width:50px; height:50px; background:#f1f5f9; border-radius:6px;"></div>'
                        }
                        <div style="flex: 1; min-width: 0;">
                            <strong style="display: block; font-size: 0.9rem; margin-bottom: 2px;">${dateStr}</strong>
                            <small class="muted" style="font-size: 0.8rem; display: block;">
                                Status: ${session.status} • ${styleLabel}
                            </small>
                        </div>
                    </div>
                `;
            },
            'Keine Foto-Sessions gefunden.'
        );
    } catch (error) {
        console.warn('Fehler beim Laden der Fotos:', error);
    }
};

const setSelectedOllamaModel = (modelName) => {
    if (!ollamaSelectedLabel) return;
    if (modelName) {
        localStorage.setItem(OLLAMA_MODEL_KEY, modelName);
        ollamaSelectedLabel.textContent = modelName;
    } else {
        localStorage.removeItem(OLLAMA_MODEL_KEY);
        ollamaSelectedLabel.textContent = 'Kein Modell gewählt';
    }
};

const setSelectedComfyCheckpoint = (checkpointName) => {
    if (!comfySelectedLabel) return;
    if (checkpointName) {
        localStorage.setItem(COMFY_CHECKPOINT_KEY, checkpointName);
        comfySelectedLabel.textContent = checkpointName;
    } else {
        localStorage.removeItem(COMFY_CHECKPOINT_KEY);
        comfySelectedLabel.textContent = 'Server-Standard';
    }
    if (photoCheckpointSelect) {
        photoCheckpointSelect.value = checkpointName || '';
    }
};

const fillPhotoCheckpointOptions = (models = [], preferredSelection = '') => {
    if (!photoCheckpointSelect) return;
    const savedSelection = preferredSelection || localStorage.getItem(COMFY_CHECKPOINT_KEY) || '';
    photoCheckpointSelect.innerHTML = '';
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Server-Standard';
    photoCheckpointSelect.appendChild(defaultOption);

    models.forEach((model) => {
        const option = document.createElement('option');
        option.value = model.name;
        option.textContent = model.name;
        photoCheckpointSelect.appendChild(option);
    });

    if (savedSelection && models.some((model) => model.name === savedSelection)) {
        photoCheckpointSelect.value = savedSelection;
    } else {
        photoCheckpointSelect.value = '';
    }
};

const renderOllamaModels = (models = []) => {
    if (!ollamaModelsContainer) return;
    const savedSelection = localStorage.getItem(OLLAMA_MODEL_KEY) || '';
    ollamaModelsContainer.innerHTML = '';
    if (!models.length) {
        ollamaModelsContainer.textContent = 'Keine Modelle gefunden.';
        ollamaModelsContainer.classList.add('muted');
        return;
    }
    const select = document.createElement('select');
    select.id = 'ollama-model-select';
    select.name = 'ollama-model';
    select.className = 'model-select';

    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Modell auswählen';
    placeholder.disabled = true;
    select.appendChild(placeholder);

    models.forEach((model) => {
        const option = document.createElement('option');
        const size = formatBytes(model.size);
        const modified = formatDate(model.modified_at);
        const meta = [size, modified ? `aktualisiert ${modified}` : ''].filter(Boolean).join(' • ');
        option.value = model.name;
        option.textContent = meta ? `${model.name} — ${meta}` : model.name;
        if (model.name === savedSelection) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    const shouldDefaultToFirst = !savedSelection && models[0];
    if (shouldDefaultToFirst) {
        select.value = models[0].name;
        setSelectedOllamaModel(models[0].name);
    } else if (savedSelection) {
        setSelectedOllamaModel(savedSelection);
    }

    ollamaModelsContainer.classList.remove('muted');
    ollamaModelsContainer.appendChild(select);
};

const renderComfyModels = (models = []) => {
    if (!comfyModelsContainer) return;
    const savedSelection = localStorage.getItem(COMFY_CHECKPOINT_KEY) || '';
    comfyModelsContainer.innerHTML = '';
    if (!models.length) {
        comfyModelsContainer.textContent = 'Keine Checkpoints gefunden.';
        comfyModelsContainer.classList.add('muted');
        fillPhotoCheckpointOptions([], '');
        return;
    }

    const select = document.createElement('select');
    select.id = 'comfy-model-select';
    select.name = 'comfy-model';
    select.className = 'model-select';

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Server-Standard';
    select.appendChild(defaultOption);

    models.forEach((model) => {
        const option = document.createElement('option');
        option.value = model.name;
        option.textContent = model.name;
        if (model.name === savedSelection) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    if (savedSelection && models.some((model) => model.name === savedSelection)) {
        setSelectedComfyCheckpoint(savedSelection);
        select.value = savedSelection;
    } else {
        setSelectedComfyCheckpoint('');
        select.value = '';
    }

    comfyModelsContainer.classList.remove('muted');
    comfyModelsContainer.appendChild(select);
    fillPhotoCheckpointOptions(models, savedSelection);
};

const scanOllamaModels = async () => {
    if (!ollamaScanBtn || !ollamaStatus) return;
    ollamaScanBtn.disabled = true;
    ollamaScanBtn.textContent = 'Scan läuft...';
    ollamaStatus.textContent = 'Suche nach Ollama Modellen...';
    setChatStatus(isAuthenticated ? 'offline' : 'needs-auth');
    try {
        const data = await api('/api/ollama/models/');
        const models = data.models || [];
        renderOllamaModels(models);
        ollamaStatus.textContent = `${models.length} Modell(e) gefunden.`;
        ollamaReady = models.length > 0;
        if (ollamaReady) {
            setChatStatus(isAuthenticated ? 'ready' : 'needs-auth');
        } else {
            setChatStatus(isAuthenticated ? 'offline' : 'needs-auth');
        }
        if (!models.length) {
            statusBar('Keine Ollama-Modelle gefunden.', 'info');
        }
    } catch (error) {
        ollamaStatus.textContent = 'Scan fehlgeschlagen.';
        statusBar(error.message, 'error');
        ollamaReady = false;
        setChatStatus('offline');
    } finally {
        ollamaScanBtn.disabled = false;
        ollamaScanBtn.textContent = 'Ollama scannen';
    }
};

const scanComfyModels = async () => {
    if (!comfyScanBtn || !comfyStatus) return;
    comfyScanBtn.disabled = true;
    comfyScanBtn.textContent = 'Scan läuft...';
    comfyStatus.textContent = 'Suche nach ComfyUI Checkpoints...';
    try {
        const data = await api('/api/comfy/models/');
        const models = data.models || [];
        renderComfyModels(models);
        comfyStatus.textContent = `${models.length} Checkpoint(s) gefunden.`;
        if (!models.length) {
            statusBar('Keine ComfyUI-Checkpoints gefunden.', 'info');
        }
    } catch (error) {
        comfyStatus.textContent = 'Scan fehlgeschlagen.';
        statusBar(error.message, 'error');
    } finally {
        comfyScanBtn.disabled = false;
        comfyScanBtn.textContent = 'ComfyUI scannen';
    }
};

if (ollamaScanBtn) {
    ollamaScanBtn.addEventListener('click', scanOllamaModels);
}
if (ollamaModelsContainer) {
    ollamaModelsContainer.addEventListener('change', (event) => {
        if (event.target.id === 'ollama-model-select') {
            setSelectedOllamaModel(event.target.value);
            statusBar('Modell übernommen.', 'success');
        }
    });
}
if (ollamaSelectedLabel) {
    setSelectedOllamaModel(localStorage.getItem(OLLAMA_MODEL_KEY));
}
if (ollamaModelsContainer && ollamaScanBtn && ollamaStatus) {
    scanOllamaModels();
}

if (comfyScanBtn) {
    comfyScanBtn.addEventListener('click', scanComfyModels);
}
if (comfyModelsContainer) {
    comfyModelsContainer.addEventListener('change', (event) => {
        if (event.target.id === 'comfy-model-select') {
            setSelectedComfyCheckpoint(event.target.value);
            statusBar('Checkpoint übernommen.', 'success');
        }
    });
}
if (photoCheckpointSelect) {
    photoCheckpointSelect.addEventListener('change', (event) => {
        setSelectedComfyCheckpoint(event.target.value);
    });
}
if (comfySelectedLabel) {
    setSelectedComfyCheckpoint(localStorage.getItem(COMFY_CHECKPOINT_KEY));
}
if (comfyModelsContainer && comfyScanBtn && comfyStatus) {
    scanComfyModels();
}

const loadApplication = (id) => {
    const app = applicationCache[id];
    currentDraftId = app.id;
    console.log("Bearbeite ID:", currentDraftId);
    if (!app || !assistantEditor) return;
    setPage('anschreiben');
    assistantEditor.innerHTML = app.cover_letter || '';
    assistantEditor.focus();
    if (assistantMeta) {
        assistantMeta.textContent = `${app.job_title} – ${app.company || ''}`;
    }
    
    if (app.structure) {
        structureContent.Einleitung = app.structure.Einleitung || '';
        structureContent.Hauptteil = app.structure.Hauptteil || '';
        structureContent.Schluss = app.structure.Schluss || '';
        updateStructureUI();
    }

    if (assistantForm) {
        const formData = new FormData(assistantForm);
        if (formData.get('job_title') !== undefined) {
            assistantForm.querySelector('input[name="job_title"]').value = app.job_title || '';
        }
        if (formData.get('company') !== undefined) {
            assistantForm.querySelector('input[name="company"]').value = app.company || '';
        }
        const descInput = assistantForm.querySelector('[name="job_description"]');
        if (descInput) {
            descInput.value = app.job_description || '';
        }
        if (toneInput && app.tone) {
            toneInput.value = app.tone;
            if (toneChips) {
                toneChips.querySelectorAll('button').forEach((btn) =>
                    btn.classList.toggle('active', btn.dataset.tone === app.tone)
                );
            }
        }
    }
};

const deleteApplication = async (id) => {
    if (!isAuthenticated) {
        statusBar('Bitte einloggen.', 'error');
        return;
    }
    const app = applicationCache[id];
    const title = app ? `${app.job_title} – ${app.company || ''}` : 'Entwurf';
    const confirmDelete = window.confirm(`Anschreiben "${title}" löschen?`);
    if (!confirmDelete) return;
    try {
        await api('/api/assistant/delete/', { method: 'POST', body: { id } });
        statusBar('Anschreiben gelöscht', 'success');
        await refreshApplications();
    } catch (error) {
        statusBar(error.message, 'error');
    }
};

const sendChatMessage = async () => {
    const text = chatBoxInput?.value.trim();
    if (!text) {
        statusBar('Keine Nachricht eingetragen.', 'error');
        return;
    }
    if (!isAuthenticated) {
        statusBar('Bitte einloggen, um den Chat zu nutzen.', 'error');
        appendChatNotice('Login erforderlich, um den LLM-Chat zu starten.');
        return;
    }
    const model = localStorage.getItem(OLLAMA_MODEL_KEY) || undefined;
    
    const formData = assistantForm ? new FormData(assistantForm) : null;
    const job_title = formData?.get('job_title') || '';
    const company = formData?.get('company') || '';
    const job_description = formData?.get('job_description') || '';
    const tone = toneInput?.value || 'formal';

    chatMessages.push({ role: 'user', content: text });
    appendChatMessage('user', text);
    chatBoxInput.value = '';
    if (chatSend) {
        setButtonLoading(chatSend, true, 'Generiere...');
    }
    setChatStatus('loading');
    try {
        pushToHistory();
        const data = await api('/api/assistant/chat/', {
            method: 'POST',
            body: { 
                message: text, 
                current_intro: structureContent.Einleitung,
                current_body: structureContent.Hauptteil,
                current_outro: structureContent.Schluss,
                is_locked_intro: structureLocks.Einleitung,
                is_locked_body: structureLocks.Hauptteil,
                is_locked_outro: structureLocks.Schluss,
                job_title, 
                company,
                job_description,
                tone, 
                model 
            },
        });
        
        const reply = data.reply || 'Änderungen vorgenommen.';
        appendChatMessage('system', reply);
        
        if (data.structure) {
            structureContent.Einleitung = data.structure.Einleitung;
            structureContent.Hauptteil = data.structure.Hauptteil;
            structureContent.Schluss = data.structure.Schluss;
        }

        if (assistantEditor && data.cover_letter) {
            assistantEditor.innerHTML = data.cover_letter;
        }

        updateStructureUI();
        pushToHistory();

        if (assistantEditor) assistantEditor.focus();
        statusBar('Anschreiben aktualisiert', 'success');

    } catch (error) {
        statusBar(error.message, 'error');
        appendChatMessage('system', `Fehler: ${error.message}`);
    } finally {
        if (chatSend) {
            setButtonLoading(chatSend, false);
        }
        setChatStatus('ready');
    }
};

const updatePhotoPreview = () => {
    if (!photoFileInput || !photoPreviewInput || !photoFileName) return;
    const file = photoFileInput.files?.[0];
    if (!file) {
        photoPreviewInput.src = 'https://placehold.co/640x400/e2e8f0/475569?text=Upload+Portrait';
        photoFileName.textContent = 'Noch kein Foto gewählt';
        return;
    }
    photoFileName.textContent = file.name;
    const reader = new FileReader();
    reader.onload = (event) => {
        if (event.target?.result) {
            photoPreviewInput.src = event.target.result;
        }
    };
    reader.readAsDataURL(file);
};

const renderPhotoOutput = (session) => {
    if (!photoPreviewOutput || !photoOutputPlaceholder) return;
    const resultUrl = session?.result_image;
    if (resultUrl) {
        photoPreviewOutput.src = resultUrl;
        photoPreviewOutput.classList.remove('hidden');
        photoOutputPlaceholder.classList.add('hidden');
        if (photoOutputFrame) {
            photoOutputFrame.classList.add('has-result');
        }
    } else {
        photoPreviewOutput.classList.add('hidden');
        photoOutputPlaceholder.classList.remove('hidden');
    }
};

const renderPhotoHistoryGrid = (sessions = []) => {
    if (!photoHistoryGrid) return;
    photoHistoryGrid.innerHTML = '';
    if (!sessions.length) {
        const empty = document.createElement('div');
        empty.className = 'photo-placeholder';
        empty.textContent = 'Noch keine Sessions. Starte mit einem Upload.';
        photoHistoryGrid.appendChild(empty);
        return;
    }
    sessions.forEach((session) => {
        const card = document.createElement('div');
        card.className = 'photo-history-card';
        const label = document.createElement('div');
        label.className = 'photo-history-meta';
        label.textContent = `${session.created_at.slice(0, 16)} • ${session.status}`;
        const image = document.createElement('img');
        image.alt = 'Bewerbungsfoto';
        image.src = session.result_image || session.source_image || '';
        if (!image.src) {
            image.classList.add('hidden');
        }
        card.appendChild(label);
        card.appendChild(image);
        photoHistoryGrid.appendChild(card);
    });
};

const refreshPhotoHistoryGrid = async () => {
    if (!photoHistoryGrid) return;
    try {
        const data = await api('/api/photos/history/');
        renderPhotoHistoryGrid(data.photo_sessions || []);
    } catch (error) {
        statusBar('Keine Berechtigung: bitte einloggen.', 'error');
    }
};

const submitPhotoForm = async (event) => {
    event.preventDefault();
    if (!isAuthenticated) {
        statusBar('Bitte zuerst einloggen.', 'error');
        return;
    }
    if (!photoFileInput?.files?.length) {
        statusBar('Bitte ein Foto auswählen.', 'error');
        return;
    }

    const formData = new FormData(photoForm);
    const savedCheckpoint = localStorage.getItem(COMFY_CHECKPOINT_KEY) || '';
    if (!formData.get('checkpoint') && savedCheckpoint) {
        formData.set('checkpoint', savedCheckpoint);
    }

    try {
        setButtonLoading(photoSubmitBtn, true, 'Generiere...');
        const data = await api('/api/photos/generate/', { method: 'POST', body: formData });
        if (data.photo_session) {
            renderPhotoOutput(data.photo_session);
        }
        statusBar('Foto erstellt', 'success');
        await refreshPhotoHistoryGrid();
    } catch (error) {
        statusBar(error.message, 'error');
    } finally {
        setButtonLoading(photoSubmitBtn, false);
    }
};

if (loadBookmarksBtn) {
    loadBookmarksBtn.addEventListener('click', refreshBookmarks);
}
if (loadApplicationsBtn) {
    loadApplicationsBtn.addEventListener('click', refreshApplications);
}
if (loadPhotosBtn) {
    loadPhotosBtn.addEventListener('click', refreshPhotos);
}

if (applicationListEl) {
    applicationListEl.addEventListener('click', (event) => {
        const target = event.target;
        if (target.matches('button[data-app-id][data-action="load"]')) {
            loadApplication(target.dataset.appId);
        }
        if (target.matches('button[data-app-id][data-action="delete"]')) {
            deleteApplication(target.dataset.appId);
        }
    });
}
if (bookmarkListEl) {
    bookmarkListEl.addEventListener('click', async (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;

        const id = btn.dataset.jobId;
        const action = btn.dataset.action;

        if (!id || !action) return;

        if (action === 'load') {
            currentJobId = id;

            currentDraftId = null;

            if (assistantEditor) {
                assistantEditor.innerHTML = '';
            }

            structureContent.Einleitung = '';
            structureContent.Hauptteil = '';
            structureContent.Schluss = '';

            structurePrompts.Einleitung = '';
            structurePrompts.Hauptteil = '';
            structurePrompts.Schluss = '';

            structureLocks.Einleitung = false;
            structureLocks.Hauptteil = false;
            structureLocks.Schluss = false;

            updateStructureUI();

            console.log("Job geladen");

            const jobData = applicationCache['job_' + id];
            if (jobData) {
                const form = document.getElementById('assistant-form');
                if (form) {
                    const titleField = form.querySelector('[name="job_title"]');
                    const companyField = form.querySelector('[name="company"]');
                    const descField = form.querySelector('[name="job_description"]');

                    if (titleField) titleField.value = jobData.title || '';
                    if (companyField) companyField.value = jobData.company || '';
                    if (descField) descField.value = jobData.description || '';

                    statusBar('Job geladen', 'success');

                    setPage('anschreiben');
                }
            }
        }

        if (action === 'delete') {
            if (!confirm("Diesen Job aus der Merkliste entfernen?")) return;

            try {
                await api('/api/jobs/bookmarks/delete/', {
                    method: 'POST',
                    body: { id }
                });

                statusBar('Job gelöscht', 'success');
                refreshBookmarks();

                if (currentJobId === id) {
                    currentJobId = null;
                }

            } catch (error) {
                console.error(error);
                statusBar('Fehler beim Löschen', 'error');
            }
        }
    });
}

if (chatSend) {
    chatSend.addEventListener('click', sendChatMessage);
}
if (chatBoxInput) {
    chatBoxInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendChatMessage();
        }
    });
}

if (photoFileInput) {
    photoFileInput.addEventListener('change', updatePhotoPreview);
}
if (photoForm) {
    photoForm.addEventListener('submit', submitPhotoForm);
}
if (refreshPhotoHistoryBtn) {
    refreshPhotoHistoryBtn.addEventListener('click', refreshPhotoHistoryGrid);
}

fetchSession();
ensureApplicationsLoaded();
syncLLMAccessWarnings();

const fillExampleBtn = document.getElementById('fill-example');

if (fillExampleBtn) {
    fillExampleBtn.addEventListener('click', () => {
        const form = document.getElementById('assistant-form');
        if (!form) return;

        const titleField = form.querySelector('[name="job_title"]');
        const companyField = form.querySelector('[name="company"]');
        const descField = form.querySelector('[name="job_description"]');
        const linkField = form.querySelector('[name="job_link"]');

        if (titleField) titleField.value = 'Junior AI Developer';
        if (companyField) companyField.value = 'Anders & Ganz GmbH';
        if (linkField) linkField.value = 'https://www.absolventa.de/stellenangebote/11244367-b-junior-ai-developer-w-m-d';
        if (descField) {
            descField.value = `Über uns:
- Wer wir sind und was wir tun
- Wir unterstützen unsere Kunden dabei, ihre Prozesse und damit ihre Organisation zu digitalisieren
- Diese Veränderung verstehen wir als ganzheitliche Aufgabe, die alle Organisationseinheiten und Hierarchiestufen einschließt
- Dazu agieren wir als verlässlicher Partner auf Augenhöhe, der seine Kunden mit technologischer, betriebswirtschaftlicher und kommunikativer Kompetenz durch den digitalen Wandel begleitet

Unsere Kultur und Grundsätze:
- Was wir tun, muss uns Freude machen - zu jedem Zeitpunkt
- Wir nehmen nur Projekte an, die uns im positiven Sinne herausfordern und weiterbringen
- Jede Zusammenarbeit ist von einem Miteinander auf Augenhöhe geprägt - im internen wie externen Team
- Kompetenz schlägt Hierarchie - immer
- Wir gehen offen miteinander um und leben Transparenz

Motivation der Position:
- Um gemeinsam mit unseren Kunden noch erfolgreicher zu sein, suchen wir einen "Junior AI Developer" (w/m/d).

Das macht Deinen Job aus: 
- Konzipieren und Entwickeln von generativen KI-Anwendungen und KI-Agentensystemen für unsere Kunden

Aufgaben: 
- Mitwirken an Bedarfsanalysen und Konzipieren von Kundenlösungen
- Datenvorbereitung und -analyse
- Schwerpunkt Entwickeln von Anwendungen mit modernen KI-Frameworks und APIs sowie eigenen Bibliotheken in Python
- Testen von Code und Anwendungen
- Wartung und Bugfixing ausgelieferter KI-Lösungen.

Bereich: 
- Die Position ist dem Bereich/Team „AI“ zugeordnet
- Deine Führungskraft ist vom Fach
- Sie kann Dir fachkompetent Rückmeldung und Unterstützung geben.

Berührungs- und Kontaktpunkte: 
- Du hast regelmäßig Kontakt zu Kunden sowie zu Kolleginnen und Kollegen aus anderen Bereichen.

Das bringst Du mit:
- Nachweisbare Python-Programmierkenntnisse - aus dem Studium oder aus erster Berufserfahrung
- Starkes Interesse an Methoden und Architekturen modernen KI-Lösungen
- Fähigkeit und Motivation, sich rasch in neue Fragestellungen und Technologien einzuarbeiten.
- Studium eines MINT-Fachs oder Data Science mit Master-Abschluss
- Fachfremde und Autodidakten mit entsprechender Berufserfahrung willkommen.
- Hands-on-Mentalität - Hohes Maß an Verantwortungsbewusstsein und Selbstständigkeit.
- Englischkenntnisse C1 oder höher, Deutschkenntnisse C1 oder höher.`;
        }

        statusBar('Beispieldaten eingefügt', 'success');
    });
}
let currentDraftId = null;

const triggerAutoSave = debounce(async () => {
    if (!isAuthenticated) return;
    const form = document.getElementById('assistant-form');
    if (!form) return;

    const editorText = assistantEditor ? assistantEditor.innerText.trim() : '';

    if (!currentDraftId && editorText.length === 0) {
        return;
    }

    const title = form.querySelector('[name="job_title"]').value;
    const company = form.querySelector('[name="company"]').value;
    const desc = form.querySelector('[name="job_description"]').value;
    const tone = document.getElementById('tone-input')?.value || 'formal';
    const model = localStorage.getItem('applai_ollama_model') || '';
    const html = assistantEditor ? assistantEditor.innerHTML : '';

    const metaEl = document.getElementById('assistant-meta');
    if (metaEl) metaEl.textContent = 'Speichert...';

    try {
        const payload = {
            id: currentDraftId,
            job_title: title,
            company: company,
            job_description: desc,
            tone: tone,
            model: model,
            cover_letter: html,
            match_notes: currentDraftId ? '' : 'Entwurf',
            section_intro: structureContent.Einleitung,
            section_body: structureContent.Hauptteil,
            section_outro: structureContent.Schluss
        };

        const data = await api('/api/assistant/save/', { method: 'POST', body: payload });

        if (data.application && data.application.id) {
            currentDraftId = data.application.id;
        }

        if (metaEl) {
            metaEl.textContent = 'Gespeichert';
            setTimeout(() => {
                if(metaEl.textContent === 'Gespeichert')
                    metaEl.textContent = `${title} – ${company}`;
            }, 1000);
        }

    } catch (error) {
        console.error("Auto-Save Error:", error);
    }
}, 1000);

const autoSaveInputs = document.querySelectorAll('#assistant-form input, #assistant-form textarea');
if (autoSaveInputs) {
    autoSaveInputs.forEach(input => {
        input.addEventListener('input', triggerAutoSave);
    });
}

if (assistantEditor) {
    assistantEditor.addEventListener('input', () => {
        triggerAutoSave();
    });
}

let currentJobId = null;

const triggerJobAutoSave = debounce(async () => {
    if (!isAuthenticated) return;

    const form = document.getElementById('assistant-form');
    if (!form) return;

    const title = form.querySelector('[name="job_title"]').value.trim();
    const company = form.querySelector('[name="company"]').value.trim();
    const desc = form.querySelector('[name="job_description"]').value.trim();

    if (!title) return;
    if (!currentJobId && !company && !desc) return;

    try {
        const payload = {
            id: currentJobId,
            title: title,
            company: company,
            description: desc,
            location: '',
            link: '',
        };

        const data = await api('/api/jobs/bookmarks/', { method: 'POST', body: payload });

        if (data.bookmark && data.bookmark.id) {
            currentJobId = data.bookmark.id;
        }

        if (document.getElementById('bookmark-list').children.length > 0) {
             refreshBookmarks();
        }

    } catch (error) {
        console.error(error);
    }
}, 1000);

const jobInputs = document.querySelectorAll('input[name="job_title"], input[name="company"], textarea[name="job_description"]');
if (jobInputs) {
    jobInputs.forEach(input => {
        input.addEventListener('input', () => {
            triggerJobAutoSave();
        });
    });
}

if (bookmarkListEl) {
    bookmarkListEl.addEventListener('click', (e) => {
        if (e.target.matches('button[data-job-id]')) {
            const id = e.target.dataset.jobId;
            currentJobId = id;
            const jobData = applicationCache['job_' + id];

            if (jobData) {
                const form = document.getElementById('assistant-form');
                if (form) {
                    const titleField = form.querySelector('[name="job_title"]');
                    const companyField = form.querySelector('[name="company"]');
                    const descField = form.querySelector('[name="job_description"]');

                    if (titleField) titleField.value = jobData.title || '';
                    if (companyField) companyField.value = jobData.company || '';
                    if (descField) descField.value = jobData.description || '';

                    statusBar('Job-Daten übernommen', 'success');
                }
            } else {
                console.error(id);
            }
        }
    });
}

const initialPage = localStorage.getItem('applai_page') || document.querySelector('.page.active')?.dataset.page || 'anschreiben';
setPage(initialPage);