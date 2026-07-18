function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

function showAlert(message) {
    return new Promise(resolve => {
        const overlay = document.getElementById('app-modal');
        const msgEl = document.getElementById('modal-message');
        const okBtn = document.getElementById('modal-ok');
        const cancelBtn = document.getElementById('modal-cancel');
        msgEl.textContent = message;
        cancelBtn.classList.add('hidden');
        overlay.classList.remove('hidden');
        const done = () => { overlay.classList.add('hidden'); okBtn.removeEventListener('click', done); resolve(); };
        okBtn.addEventListener('click', done);
    });
}

function showConfirm(message, cancelLabel) {
    return new Promise(resolve => {
        const overlay = document.getElementById('app-modal');
        const msgEl = document.getElementById('modal-message');
        const okBtn = document.getElementById('modal-ok');
        const cancelBtn = document.getElementById('modal-cancel');
        msgEl.textContent = message;
        cancelBtn.textContent = cancelLabel || 'キャンセル';
        cancelBtn.classList.remove('hidden');
        overlay.classList.remove('hidden');
        const onOk = () => { cleanup(); resolve(true); };
        const onCancel = () => { cleanup(); resolve(false); };
        const cleanup = () => {
            overlay.classList.add('hidden');
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
        };
        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
    });
}

function showPrompt(message, defaultValue, cancelLabel) {
    return new Promise(resolve => {
        const overlay = document.getElementById('app-modal');
        const msgEl = document.getElementById('modal-message');
        const inputEl = document.getElementById('modal-input');
        const okBtn = document.getElementById('modal-ok');
        const cancelBtn = document.getElementById('modal-cancel');
        msgEl.textContent = message;
        inputEl.value = defaultValue || '';
        inputEl.classList.remove('hidden');
        cancelBtn.textContent = cancelLabel || 'キャンセル';
        cancelBtn.classList.remove('hidden');
        overlay.classList.remove('hidden');
        inputEl.focus();
        const onOk = () => { const val = inputEl.value.trim(); cleanup(); resolve(val || null); };
        const onCancel = () => { cleanup(); resolve(null); };
        const onKeydown = (e) => {
            if (e.key === 'Enter') { e.preventDefault(); onOk(); }
            else if (e.key === 'Escape') { onCancel(); }
        };
        const cleanup = () => {
            overlay.classList.add('hidden');
            inputEl.classList.add('hidden');
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
            inputEl.removeEventListener('keydown', onKeydown);
        };
        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
        inputEl.addEventListener('keydown', onKeydown);
    });
}

// Legacy single-profile key, kept only as a migration source (issue #31).
const STORAGE_KEY = 'photoArrangerSettings';
// New multi-profile storage key: { activeProfile, profiles: [{ name, settings }] }
const PROFILES_KEY = 'photoArrangerProfiles';

function getCurrentFormSettings() {
    const srcDirInputs = document.querySelectorAll('.src-dir-input');
    const srcDirs = Array.from(srcDirInputs).map(i => i.value);
    const dstDir = document.getElementById('dst-dir') ? document.getElementById('dst-dir').value : '';
    const namingRule = document.getElementById('naming-rule') ? document.getElementById('naming-rule').value : '';
    const customTemplate = document.getElementById('custom-template') ? document.getElementById('custom-template').value : '';
    const extCheckboxes = document.querySelectorAll('input[name="extensions"]');
    const extensions = Array.from(extCheckboxes).filter(cb => cb.checked).map(cb => cb.value);
    const dateStart = document.getElementById('date-start') ? document.getElementById('date-start').value : '';
    const dateEnd = document.getElementById('date-end') ? document.getElementById('date-end').value : '';
    const modeEl = document.querySelector('.toggle-option.active');
    const mode = modeEl ? modeEl.getAttribute('data-value') : 'copy';
    const recursiveEl = document.getElementById('recursive-scan');
    const recursive = recursiveEl ? recursiveEl.checked : false;
    const lang = document.querySelector('.lang-option.active');
    const language = lang ? (lang.id === 'btn-lang-en' ? 'en' : 'ja') : 'ja';
    return { srcDirs, dstDir, namingRule, customTemplate, extensions, dateStart, dateEnd, mode, language, recursive };
}

function loadProfilesStore() {
    try {
        const raw = localStorage.getItem(PROFILES_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed || !Array.isArray(parsed.profiles) || parsed.profiles.length === 0) return null;
        return parsed;
    } catch (e) {
        return null;
    }
}

function saveProfilesStore(store) {
    try {
        localStorage.setItem(PROFILES_KEY, JSON.stringify(store));
    } catch (e) { /* storage unavailable */ }
}

// Migrates the legacy single-profile localStorage format (pre-#31) into the
// new named-profiles format, wrapping any existing settings into a single
// "Default"/"デフォルト" profile so returning users don't lose their settings.
function migrateLegacySettingsIfNeeded() {
    const existing = loadProfilesStore();
    if (existing) return existing;

    let legacySettings = null;
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) legacySettings = JSON.parse(raw);
    } catch (e) { /* corrupt legacy data - ignore */ }

    const language = legacySettings && legacySettings.language === 'en' ? 'en' : 'ja';
    const defaultName = language === 'en' ? 'Default' : 'デフォルト';

    const store = {
        activeProfile: defaultName,
        profiles: [{ name: defaultName, settings: legacySettings || getCurrentFormSettings() }]
    };
    saveProfilesStore(store);
    return store;
}

function saveSettings() {
    try {
        const store = loadProfilesStore() || migrateLegacySettingsIfNeeded();
        const idx = store.profiles.findIndex(p => p.name === store.activeProfile);
        if (idx === -1) return;
        store.profiles[idx].settings = getCurrentFormSettings();
        saveProfilesStore(store);
    } catch (e) { /* storage unavailable */ }
}

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const srcDirsContainer = document.getElementById('src-dirs-container');
    const btnAddSrc = document.getElementById('btn-add-src');
    const dstDirInput = document.getElementById('dst-dir');
    const btnSelectDst = document.getElementById('btn-select-dst');
    const btnStart = document.getElementById('btn-start');
    const btnDryRun = document.getElementById('btn-dryrun');
    const btnClearLog = document.getElementById('btn-clear-log');
    const btnCancel = document.getElementById('btn-cancel');
    const btnShutdown = document.getElementById('btn-shutdown');
    const namingRuleSelect = document.getElementById('naming-rule');

    const profileSelect = document.getElementById('profile-select');
    const btnProfileSave = document.getElementById('btn-profile-save');
    const btnProfileSaveAs = document.getElementById('btn-profile-save-as');
    const btnProfileDelete = document.getElementById('btn-profile-delete');

    const progressCard = document.getElementById('progress-card');
    const progressPercent = document.getElementById('progress-percent');
    const progressBar = document.getElementById('progress-bar');
    const progressTitle = document.getElementById('progress-title');
    const progressIcon = document.getElementById('progress-icon');
    const currentFilename = document.getElementById('current-filename');
    
    const previewCard = document.getElementById('preview-card');
    const previewCount = document.getElementById('preview-count');
    const previewList = document.getElementById('preview-list');
    
    const statTotal = document.getElementById('stat-total');
    const statCopied = document.getElementById('stat-copied');
    const statCopiedLabel = document.getElementById('stat-copied-label');
    const statSkipped = document.getElementById('stat-skipped');
    const statErrors = document.getElementById('stat-errors');
    
    const logCard = document.getElementById('log-card');
    const logConsole = document.getElementById('log-console');
    const btnUndo = document.getElementById('btn-undo');

    const reportEmpty = document.getElementById('report-empty');
    const reportContent = document.getElementById('report-content');
    const reportTotalSessions = document.getElementById('report-total-sessions');
    const reportTotalFiles = document.getElementById('report-total-files');
    const reportCopyFiles = document.getElementById('report-copy-files');
    const reportMoveFiles = document.getElementById('report-move-files');
    const reportTotalSize = document.getElementById('report-total-size');
    const reportMonthlyList = document.getElementById('report-monthly-list');
    const btnRefreshReport = document.getElementById('btn-refresh-report');

    // Current app state
    let selectedMode = 'copy'; // Default mode
    let simulationResults = [];
    let currentLang = 'ja';
    let lastReportData = null;
    let thumbObjectUrls = [];

    // Lazily fetches and displays thumbnails for the Dry Run preview list once a
    // row scrolls into view, avoiding upfront requests for every result.
    const thumbObserver = ('IntersectionObserver' in window)
        ? new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    obs.unobserve(entry.target);
                    loadThumbnail(entry.target);
                }
            });
        }, { root: previewList, rootMargin: '100px' })
        : null;

    async function loadThumbnail(imgEl) {
        const fullPath = imgEl.dataset.fullPath;
        const srcDir = imgEl.dataset.srcDir;
        if (!fullPath || !srcDir) {
            imgEl.classList.add('thumb-error');
            return;
        }
        try {
            const params = new URLSearchParams();
            params.set('path', fullPath);
            params.append('src_dir', srcDir);
            const response = await fetch(`/api/thumbnail?${params.toString()}`, {
                headers: { 'X-CSRF-Token': getCsrfToken() },
            });
            if (!response.ok) throw new Error('thumbnail unavailable');
            const blob = await response.blob();
            const objectUrl = URL.createObjectURL(blob);
            thumbObjectUrls.push(objectUrl);
            imgEl.src = objectUrl;
            imgEl.classList.add('loaded');
        } catch (error) {
            imgEl.classList.add('thumb-error');
        }
    }

    function clearThumbnailUrls() {
        thumbObjectUrls.forEach(url => URL.revokeObjectURL(url));
        thumbObjectUrls = [];
    }

    // Toggle mode buttons
    const toggleOptions = document.querySelectorAll('.toggle-option');
    toggleOptions.forEach(option => {
        option.addEventListener('click', () => {
            toggleOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
            selectedMode = option.getAttribute('data-value');
            updateStatsLabels();
            saveSettings();
        });
    });

    // Folder selection helper
    async function selectDirectory(targetInput) {
        try {
            targetInput.disabled = true;
            const response = await fetch('/api/select-dir', {
                method: 'POST',
                headers: { 'X-CSRF-Token': getCsrfToken() },
            });
            const data = await response.json();
            
            if (data.path) {
                targetInput.value = data.path;
                saveSettings();
            } else if (data.error) {
                addLog(`フォルダ選択エラー: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Directory selection failed:', error);
            addLog('フォルダ選択ダイアログの起動に失敗しました。', 'error');
        } finally {
            targetInput.disabled = false;
        }
    }

    // Dynamic rows event delegation
    srcDirsContainer.addEventListener('click', (e) => {
        const btnSelect = e.target.closest('.btn-select-src');
        if (btnSelect) {
            const input = btnSelect.parentElement.querySelector('.src-dir-input');
            if (input) selectDirectory(input);
            return;
        }

        const btnRemove = e.target.closest('.btn-remove-src');
        if (btnRemove) {
            const row = btnRemove.closest('.src-dir-row');
            if (row) {
                row.remove();
                updateRemoveButtonsVisibility();
                saveSettings();
            }
        }
    });

    // Add source row
    btnAddSrc.addEventListener('click', () => {
        const newRow = document.createElement('div');
        newRow.className = 'input-with-btn src-dir-row';
        newRow.innerHTML = `
            <input type="text" class="src-dir-input" placeholder="${currentLang === 'ja' ? '整理する写真が入っているフォルダのパス' : 'Path to folder containing photos to organize'}" spellcheck="false">
            <button type="button" class="btn btn-secondary btn-select-src">
                <i class="fa-solid fa-magnifying-glass"></i> ${currentLang === 'ja' ? '選択' : 'Select'}
            </button>
            <button type="button" class="btn btn-danger btn-remove-src">
                <i class="fa-solid fa-trash-can"></i>
            </button>
        `;
        srcDirsContainer.appendChild(newRow);
        updateRemoveButtonsVisibility();
    });

    function updateRemoveButtonsVisibility() {
        const rows = srcDirsContainer.querySelectorAll('.src-dir-row');
        rows.forEach(row => {
            const removeBtn = row.querySelector('.btn-remove-src');
            if (removeBtn) {
                removeBtn.style.display = rows.length > 1 ? 'inline-flex' : 'none';
            }
        });
    }

    btnSelectDst.addEventListener('click', () => selectDirectory(dstDirInput));
    dstDirInput.addEventListener('change', saveSettings);
    srcDirsContainer.addEventListener('change', saveSettings);
    document.getElementById('naming-rule').addEventListener('change', saveSettings);
    document.getElementById('custom-template').addEventListener('input', saveSettings);
    document.querySelectorAll('input[name="extensions"]').forEach(cb => cb.addEventListener('change', saveSettings));
    document.getElementById('date-start').addEventListener('change', saveSettings);
    document.getElementById('date-end').addEventListener('change', saveSettings);
    document.getElementById('recursive-scan').addEventListener('change', saveSettings);

    // Clear logs
    btnClearLog.addEventListener('click', () => {
        logConsole.innerHTML = '';
    });

    // Cancel operation
    btnCancel.addEventListener('click', async () => {
        try {
            btnCancel.disabled = true;
            btnCancel.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${currentLang === 'ja' ? '中断中...' : 'Cancelling...'}`;
            const response = await fetch('/api/cancel', {
                method: 'POST',
                headers: { 'X-CSRF-Token': getCsrfToken() },
            });
            const data = await response.json();
            addLog(data.message, 'info');
        } catch (error) {
            console.error('Cancel request failed:', error);
            addLog('中断シグナルの送信に失敗しました。', 'error');
            btnCancel.disabled = false;
            btnCancel.innerHTML = `<i class="fa-solid fa-hand"></i> ${currentLang === 'ja' ? '中断' : 'Cancel'}`;
        }
    });

    // Shutdown screen layout
    function showShutdownScreen() {
        const dict = uiStrings[currentLang];
        document.body.innerHTML = `
            <div style="display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:100vh;color:#f3f4f6;background-color:#080b11;font-family:sans-serif;text-align:center;padding:2rem;">
                <i class="fa-solid fa-power-off" style="font-size:4rem;color:#ef4444;margin-bottom:1.5rem;text-shadow:0 0 20px rgba(239,68,68,0.4)"></i>
                <h1 style="font-size:1.8rem;margin-bottom:1rem;">${dict['shutdown-title-screen']}</h1>
                <p style="color:#9ca3af;font-size:1rem;">${dict['shutdown-desc-screen']}</p>
            </div>
        `;
    }

    // Shutdown backend server
    btnShutdown.addEventListener('click', async () => {
        const confirmMsg = uiStrings[currentLang]['shutdown-confirm'];
        const cancelLbl = currentLang === 'ja' ? 'キャンセル' : 'Cancel';
        if (!await showConfirm(confirmMsg, cancelLbl)) {
            return;
        }

        try {
            addLog('サーバーのシャットダウン要求を送信しました...', 'error');
            await fetch('/api/shutdown', {
                method: 'POST',
                headers: { 'X-CSRF-Token': getCsrfToken() },
            });
            showShutdownScreen();
        } catch (error) {
            showShutdownScreen();
        }
    });

    // Logging helper
    function addLog(message, type = 'info') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        line.textContent = `[${timestamp}] ${message}`;
        
        logConsole.appendChild(line);
        logConsole.scrollTop = logConsole.scrollHeight;
    }

    // Toggle custom template input
    namingRuleSelect.addEventListener('change', () => {
        const customTemplateGroup = document.getElementById('custom-template-group');
        if (namingRuleSelect.value === 'custom') {
            customTemplateGroup.classList.remove('hidden');
        } else {
            customTemplateGroup.classList.add('hidden');
        }
    });

    // Trigger dry-run or actual run
    btnDryRun.addEventListener('click', () => startProcessing(true));
    btnStart.addEventListener('click', () => startProcessing(false));

    async function startProcessing(dryRun = false) {
        const srcDirInputs = srcDirsContainer.querySelectorAll('.src-dir-input');
        const srcDirs = Array.from(srcDirInputs).map(input => input.value.trim()).filter(path => path !== '');
        const dstDir = dstDirInput.value.trim();
        
        const namingRule = namingRuleSelect.value === 'custom'
            ? document.getElementById('custom-template').value.trim()
            : namingRuleSelect.value;

        if (srcDirs.length === 0 || !dstDir) {
            await showAlert(uiStrings[currentLang]['error-select-dirs']);
            return;
        }

        // Get advanced options
        const extCheckboxes = document.querySelectorAll('input[name="extensions"]:checked');
        const extensions = Array.from(extCheckboxes).map(cb => cb.value);
        const dateStart = document.getElementById('date-start').value || null;
        const dateEnd = document.getElementById('date-end').value || null;

        // Reset UI state
        progressCard.classList.remove('hidden');
        logCard.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        currentFilename.textContent = currentLang === 'ja' ? 'スキャン中...' : 'Scanning...';
        btnUndo.classList.add('hidden'); // Hide undo during processing
        
        // Reset cancel button
        btnCancel.disabled = false;
        btnCancel.innerHTML = `<i class="fa-solid fa-hand"></i> ${currentLang === 'ja' ? '中断' : 'Cancel'}`;
        if (dryRun) {
            btnCancel.classList.add('hidden');
            progressTitle.textContent = currentLang === 'ja' ? 'シミュレーション中' : 'Simulating';
        } else {
            btnCancel.classList.remove('hidden');
            progressTitle.textContent = currentLang === 'ja' ? '実行中' : 'Running';
        }

        progressIcon.className = 'fa-solid fa-spinner fa-spin';
        progressIcon.style.color = '';

        statTotal.textContent = '0';
        statCopied.textContent = '0';
        statSkipped.textContent = '0';
        statErrors.textContent = '0';
        
        logConsole.innerHTML = '';
        simulationResults = [];
        
        if (dryRun) {
            previewCard.classList.add('hidden');
            clearThumbnailUrls();
            previewList.innerHTML = '';
            addLog(currentLang === 'ja' ? 'シミュレーション（Dry Run）を開始します...' : 'Starting simulation (Dry Run)...', 'info');
        } else {
            const startText = currentLang === 'ja'
                ? `整理処理 (${selectedMode === 'move' ? '移動' : 'コピー'}モード) を開始します...`
                : `Starting arrangement (${selectedMode === 'move' ? 'move' : 'copy'} mode)...`;
            addLog(startText, 'info');
        }

        setControlsDisabled(true);

        try {
            const response = await fetch('/api/arrange', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': getCsrfToken(),
                },
                body: JSON.stringify({
                    src_dirs: srcDirs,
                    dst_dir: dstDir,
                    naming_rule: namingRule,
                    mode: selectedMode,
                    dry_run: dryRun,
                    extensions: extensions.length > 0 ? extensions : null,
                    date_start: dateStart,
                    date_end: dateEnd,
                    lang: currentLang,
                    recursive: document.getElementById('recursive-scan') ? document.getElementById('recursive-scan').checked : false
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'リクエストに失敗しました。');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6).trim();
                        if (!jsonStr) continue;

                        try {
                            const data = JSON.parse(jsonStr);
                            updateProgress(data, dryRun);
                        } catch (e) {
                            console.error('Failed to parse SSE JSON:', e, jsonStr);
                        }
                    }
                }
            }

            if (buffer.startsWith('data: ')) {
                try {
                    const data = JSON.parse(buffer.slice(6).trim());
                    updateProgress(data, dryRun);
                } catch (e) {
                    console.error('Failed to parse trailing buffer:', e);
                }
            }

        } catch (error) {
            addLog(`処理失敗: ${error.message}`, 'error');
            await showAlert(`エラーが発生しました: ${error.message}`);
        } finally {
            setControlsDisabled(false);
            btnCancel.classList.add('hidden');
            
            // Check completed status icon
            if (progressPercent.textContent === '100%') {
                progressIcon.className = 'fa-solid fa-circle-check';
                progressIcon.style.color = 'var(--success)';
                progressTitle.textContent = currentLang === 'ja'
                    ? (dryRun ? 'シミュレーション完了' : '処理完了')
                    : (dryRun ? 'Simulation Completed' : 'Completed');
                
                // Show Undo button only on successful actual runs
                if (!dryRun) {
                    btnUndo.classList.remove('hidden');
                    loadReport(); // Refresh stats after files were actually organized
                }
            } else {
                progressIcon.className = 'fa-solid fa-circle-exclamation';
                progressIcon.style.color = 'var(--danger)';
                progressTitle.textContent = currentLang === 'ja' ? '処理中断' : 'Cancelled';
            }

            if (dryRun && simulationResults.length > 0) {
                renderSimulationPreview();
            }
        }
    }

    // Set control disabled states
    function setControlsDisabled(disabled) {
        btnStart.disabled = disabled;
        btnDryRun.disabled = disabled;
        btnAddSrc.disabled = disabled;
        btnSelectDst.disabled = disabled;
        dstDirInput.disabled = disabled;
        namingRuleSelect.disabled = disabled;

        const srcInputs = srcDirsContainer.querySelectorAll('.src-dir-input');
        srcInputs.forEach(input => input.disabled = disabled);

        const srcButtons = srcDirsContainer.querySelectorAll('.btn-select-src, .btn-remove-src');
        srcButtons.forEach(btn => btn.disabled = disabled);

        const toggles = document.querySelectorAll('.toggle-option');
        toggles.forEach(t => t.style.pointerEvents = disabled ? 'none' : 'auto');
    }

    // Live update UI progress
    function updateProgress(data, dryRun) {
        if (data.progress !== undefined) {
            progressBar.style.width = `${data.progress}%`;
            progressPercent.textContent = `${data.progress}%`;
        }

        if (data.current_file) {
            currentFilename.textContent = data.current_file;
        }

        if (data.message) {
            const type = data.log_type || 'info';
            addLog(data.message, type);
        }

        if (data.warning) {
            addLog(`${data.current_file || ''}: ${data.warning.message}`, 'warning');
        }

        if (dryRun && data.action) {
            simulationResults.push(data);
        }

        if (data.stats) {
            statTotal.textContent = data.stats.total;
            statCopied.textContent = data.stats.copied;
            statSkipped.textContent = data.stats.skipped;
            statErrors.textContent = data.stats.errors;
        }

        if (data.status === 'completed') {
            addLog(data.message, 'success');
            currentFilename.textContent = currentLang === 'ja' ? '完了しました。' : 'Completed.';
        }
        
        if (data.status === 'cancelled') {
            addLog(data.message, 'error');
            currentFilename.textContent = currentLang === 'ja' ? '中断されました。' : 'Cancelled.';
            progressIcon.className = 'fa-solid fa-circle-exclamation';
            progressIcon.style.color = 'var(--danger)';
            progressTitle.textContent = currentLang === 'ja' ? '処理中断' : 'Cancelled';
        }
    }

    // Render Dry Run preview list
    function renderSimulationPreview() {
        previewCard.classList.remove('hidden');
        const itemsLabel = currentLang === 'ja' ? '件' : 'items';
        const warningCount = simulationResults.filter(r => r.warning).length;
        previewCount.textContent = warningCount > 0
            ? `${simulationResults.length} ${itemsLabel} (⚠ ${warningCount})`
            : `${simulationResults.length} ${itemsLabel}`;
        clearThumbnailUrls();
        previewList.innerHTML = '';

        simulationResults.forEach(item => {
            const row = document.createElement('div');
            const displayAction = item.action || 'copy';
            const isCorrupt = item.warning && item.warning.type === 'corrupt';
            row.className = `preview-row ${displayAction}-row${item.warning ? ' has-warning' : ''}${isCorrupt ? ' corrupt-row' : ''}`;

            const badgeTextMap = {
                ja: {
                    'copy': 'コピー',
                    'move': '移動',
                    'skip': '重複スキップ',
                    'rename': 'リネーム',
                    'rename_move': '名変移動',
                    'error': 'エラー'
                },
                en: {
                    'copy': 'Copy',
                    'move': 'Move',
                    'skip': 'Skip',
                    'rename': 'Rename',
                    'rename_move': 'Ren Move',
                    'error': 'Error'
                }
            };
            const badgeClass = item.action || 'copy';
            const badgeText = badgeTextMap[currentLang][badgeClass] || badgeClass;

            const targetFilename = item.target || item.filename;
            const destDisplay = item.action.startsWith('rename') 
                ? `${item.folder}/${targetFilename}` 
                : `${item.folder}/`;

            const fileDisplay = `${escapeHtml(item.src_dir)}/${escapeHtml(item.filename)}`;
            const destEscaped = escapeHtml(destDisplay);
            const warningHtml = item.warning ? `
                <div class="preview-warning${isCorrupt ? ' corrupt' : ''}">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <span>${escapeHtml(item.warning.message)}</span>
                </div>
            ` : '';
            const hasThumbSource = Boolean(item.full_path && item.src_dir_full);
            const thumbHtml = hasThumbSource
                ? `<img class="preview-thumb" alt="" data-full-path="${escapeHtml(item.full_path)}" data-src-dir="${escapeHtml(item.src_dir_full)}">`
                : `<div class="preview-thumb preview-thumb-placeholder"><i class="fa-regular fa-image"></i></div>`;
            row.innerHTML = `
                <div class="preview-row-main">
                    ${thumbHtml}
                    <div class="preview-file" title="${fileDisplay}">
                        ${fileDisplay}
                    </div>
                    <div class="preview-details">
                        <span class="p-badge ${escapeHtml(badgeClass)}">${escapeHtml(badgeText)}</span>
                        <i class="fa-solid fa-arrow-right-long preview-arrow"></i>
                        <span class="preview-dest-folder" title="${destEscaped}">${destEscaped}</span>
                    </div>
                </div>
                ${warningHtml}
            `;
            previewList.appendChild(row);

            if (hasThumbSource) {
                const thumbEl = row.querySelector('.preview-thumb');
                if (thumbObserver) {
                    thumbObserver.observe(thumbEl);
                } else {
                    loadThumbnail(thumbEl);
                }
            }
        });
    }

    // Undo click event handler
    btnUndo.addEventListener('click', async () => {
        const confirmMsg = currentLang === 'ja'
            ? '最新の整理セッションを元に戻しますか？（コピーされたファイルは削除され、移動されたファイルは元のフォルダに戻ります）'
            : 'Rollback the latest session? (Copied files will be deleted, and moved files will be returned to their original folders)';
        if (!await showConfirm(confirmMsg, currentLang === 'ja' ? 'キャンセル' : 'Cancel')) return;

        try {
            btnUndo.disabled = true;
            btnUndo.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${currentLang === 'ja' ? '元に戻し中...' : 'Undoing...'}`;
            addLog(currentLang === 'ja' ? 'Undo処理を開始します...' : 'Starting Undo operation...', 'info');

            const response = await fetch('/api/undo', {
                method: 'POST',
                headers: { 'X-CSRF-Token': getCsrfToken() },
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Undoに失敗しました。');
            }

            addLog(data.message, 'success');
            if (data.logs && data.logs.length > 0) {
                data.logs.forEach(log => addLog(log, 'info'));
            }
            await showAlert(data.message);
            btnUndo.classList.add('hidden'); // Hide undo button after rollback succeeds
            loadReport(); // Refresh stats since the undo changed organized-file counts
        } catch (error) {
            console.error('Undo request failed:', error);
            addLog(`${currentLang === 'ja' ? 'Undo失敗' : 'Undo failed'}: ${error.message}`, 'error');
            await showAlert(`${currentLang === 'ja' ? 'Undoエラー' : 'Undo error'}: ${error.message}`);
        } finally {
            btnUndo.disabled = false;
            btnUndo.innerHTML = `<i class="fa-solid fa-rotate-left"></i> ${uiStrings[currentLang]['lbl-undo']}`;
        }
    });

    // Format a byte count into a human-readable string (B/KB/MB/GB/TB)
    function formatBytes(bytes) {
        if (!bytes || bytes <= 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let value = bytes;
        let unitIndex = 0;
        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024;
            unitIndex++;
        }
        return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
    }

    // Render the report/statistics card from aggregated /api/report data
    function renderReport(data) {
        const totals = data.totals || {};
        const monthly = data.monthly || [];

        if (!totals.total_sessions && !totals.total_files) {
            reportEmpty.classList.remove('hidden');
            reportContent.classList.add('hidden');
            return;
        }

        reportEmpty.classList.add('hidden');
        reportContent.classList.remove('hidden');

        reportTotalSessions.textContent = totals.total_sessions || 0;
        reportTotalFiles.textContent = totals.total_files || 0;
        reportCopyFiles.textContent = totals.copy_files || 0;
        reportMoveFiles.textContent = totals.move_files || 0;
        reportTotalSize.textContent = formatBytes(totals.total_size || 0);

        reportMonthlyList.innerHTML = '';
        const maxTotal = monthly.reduce((max, m) => Math.max(max, m.total_files || 0), 0) || 1;
        const copyLabel = currentLang === 'ja' ? 'コピー' : 'Copy';
        const moveLabel = currentLang === 'ja' ? '移動' : 'Move';
        const filesUnit = currentLang === 'ja' ? '件' : 'files';

        // Most recent month first
        [...monthly].reverse().forEach(m => {
            const totalFiles = m.total_files || 0;
            const copyFiles = m.copy_files || 0;
            const moveFiles = m.move_files || 0;
            const copyPct = (copyFiles / maxTotal) * 100;
            const movePct = (moveFiles / maxTotal) * 100;

            const row = document.createElement('div');
            row.className = 'report-month-row';
            row.innerHTML = `
                <div class="report-month-row-header">
                    <span class="report-month-label">${escapeHtml(m.month || '-')}</span>
                    <span class="report-month-count">${totalFiles} ${filesUnit} (${copyLabel} ${copyFiles} / ${moveLabel} ${moveFiles})</span>
                </div>
                <div class="report-bar-track">
                    <div class="report-bar-copy" style="width:${copyPct}%"></div>
                    <div class="report-bar-move" style="width:${movePct}%"></div>
                </div>
            `;
            reportMonthlyList.appendChild(row);
        });
    }

    // Fetch aggregated report data from the backend and render it
    async function loadReport() {
        try {
            if (btnRefreshReport) btnRefreshReport.disabled = true;
            const response = await fetch('/api/report');
            const data = await response.json();
            if (response.ok) {
                lastReportData = data;
                renderReport(data);
            }
        } catch (error) {
            console.error('Failed to load report:', error);
        } finally {
            if (btnRefreshReport) btnRefreshReport.disabled = false;
        }
    }

    if (btnRefreshReport) {
        btnRefreshReport.addEventListener('click', loadReport);
    }

    // i18n dynamic elements maps
    const btnLangJa = document.getElementById('btn-lang-ja');
    const btnLangEn = document.getElementById('btn-lang-en');

    const uiStrings = {
        ja: {
            'subtitle-text': 'EXIF撮影日時とファイル更新日時を自動解析して写真を整理します',
            'setup-title': '設定',
            'lbl-profile': '設定プロファイル',
            'btn-profile-save': '保存',
            'btn-profile-save-title': '現在の設定を選択中のプロファイルに上書き保存します',
            'btn-profile-save-as': '新規保存',
            'btn-profile-save-as-title': '現在の設定を新しい名前のプロファイルとして保存します',
            'btn-profile-delete-title': '選択中のプロファイルを削除します',
            'prompt-profile-name': '保存するプロファイル名を入力してください',
            'confirm-profile-overwrite': '「{name}」は既に存在します。上書きしますか？',
            'confirm-profile-delete': '「{name}」を削除しますか？',
            'error-profile-last': '最低1つのプロファイルが必要なため、これ以上削除できません。',
            'lbl-src-dirs': 'コピー元ディレクトリ',
            'placeholder-src': '整理する写真が入っているフォルダのパス',
            'btn-select': '選択',
            'btn-add-src': 'フォルダを追加',
            'lbl-dst-dir': 'コピー先ディレクトリ',
            'placeholder-dst': '整理した写真を保存するフォルダのパス',
            'lbl-mode': '処理モード',
            'lbl-copy': 'コピー',
            'lbl-move': '移動 (元ファイル削除)',
            'lbl-naming-rule': 'フォルダ命名規則',
            'opt-custom-template': 'カスタム命名テンプレート...',
            'lbl-custom-template': '命名テンプレート',
            'text-custom-tokens': '利用可能トークン: {YYYY}, {MM}, {DD}, {filename}, {ext}',
            'lbl-advanced-filters': '詳細フィルタ設定',
            'lbl-filter-extensions': '対象拡張子 (複数選択)',
            'lbl-filter-date': '対象日付範囲',
            'btn-dryrun-text': 'シミュレーション',
            'btn-start-text': '整理を実行する',
            'preview-title-text': 'シミュレーション結果プレビュー',
            'preview-desc-text': '※シミュレーションのため、実際のファイル操作は行われていません。',
            'lbl-processing-file': '処理中のファイル',
            'lbl-total-files': '総件数',
            'lbl-copied-files': 'コピー済',
            'lbl-moved-files': '移動済',
            'lbl-skipped-files': '重複スキップ',
            'lbl-error-files': 'エラー',
            'title-log': '実行ログ',
            'lbl-undo': '元に戻す (Undo)',
            'btn-clear': 'クリア',
            'shutdown-confirm': 'サーバーをシャットダウンしますか？終了すると再度起動するまでアプリは利用できなくなります。',
            'error-select-dirs': 'コピー元とコピー先のディレクトリを指定してください。',
            'shutdown-title-screen': 'サーバーを終了しました',
            'shutdown-desc-screen': 'ブラウザのタブを閉じて問題ありません。',
            'title-report': 'レポート',
            'lbl-refresh-report': '更新',
            'text-report-empty': 'まだ整理履歴がありません。',
            'lbl-report-sessions': '実行回数',
            'lbl-report-total-files': '整理済ファイル',
            'lbl-report-copy-files': 'コピー',
            'lbl-report-move-files': '移動',
            'lbl-report-total-size': '合計サイズ',
            'lbl-legend-copy': 'コピー',
            'lbl-legend-move': '移動',
            'lbl-recursive': 'サブフォルダも再帰的にスキャンする'
        },
        en: {
            'subtitle-text': 'Automatically organize photos into date folders using EXIF metadata and file mtimes',
            'setup-title': 'Settings',
            'lbl-profile': 'Settings Profile',
            'btn-profile-save': 'Save',
            'btn-profile-save-title': 'Overwrite the selected profile with the current settings',
            'btn-profile-save-as': 'Save As New',
            'btn-profile-save-as-title': 'Save the current settings as a new named profile',
            'btn-profile-delete-title': 'Delete the selected profile',
            'prompt-profile-name': 'Enter a name for this profile',
            'confirm-profile-overwrite': 'A profile named "{name}" already exists. Overwrite it?',
            'confirm-profile-delete': 'Delete profile "{name}"?',
            'error-profile-last': 'At least one profile is required, so this one cannot be deleted.',
            'lbl-src-dirs': 'Source Directory',
            'placeholder-src': 'Path to folder containing photos to organize',
            'btn-select': 'Select',
            'btn-add-src': 'Add Folder',
            'lbl-dst-dir': 'Destination Directory',
            'placeholder-dst': 'Path to folder to save organized photos',
            'lbl-mode': 'Processing Mode',
            'lbl-copy': 'Copy',
            'lbl-move': 'Move (Delete source)',
            'lbl-naming-rule': 'Folder Naming Rules',
            'opt-custom-template': 'Custom Naming Template...',
            'lbl-custom-template': 'Naming Template',
            'text-custom-tokens': 'Available tokens: {YYYY}, {MM}, {DD}, {filename}, {ext}',
            'lbl-advanced-filters': 'Advanced Filter Settings',
            'lbl-filter-extensions': 'Target Extensions (Select multiple)',
            'lbl-filter-date': 'Target Date Range',
            'btn-dryrun-text': 'Simulation',
            'btn-start-text': 'Organize Photos',
            'preview-title-text': 'Simulation Preview',
            'preview-desc-text': '* For simulation only. No files are actually modified.',
            'lbl-processing-file': 'Processing file',
            'lbl-total-files': 'Total Files',
            'lbl-copied-files': 'Copied',
            'lbl-moved-files': 'Moved',
            'lbl-skipped-files': 'Skip Duplicates',
            'lbl-error-files': 'Errors',
            'title-log': 'Execution Log',
            'lbl-undo': 'Rollback (Undo)',
            'btn-clear': 'Clear',
            'shutdown-confirm': 'Shutdown server? The app will become unavailable until started again.',
            'error-select-dirs': 'Please specify source and destination directories.',
            'shutdown-title-screen': 'Server Stopped',
            'shutdown-desc-screen': 'You can safely close this browser tab.',
            'title-report': 'Report',
            'lbl-refresh-report': 'Refresh',
            'text-report-empty': 'No arrange history yet.',
            'lbl-report-sessions': 'Runs',
            'lbl-report-total-files': 'Files Organized',
            'lbl-report-copy-files': 'Copied',
            'lbl-report-move-files': 'Moved',
            'lbl-report-total-size': 'Total Size',
            'lbl-legend-copy': 'Copy',
            'lbl-legend-move': 'Move',
            'lbl-recursive': 'Scan subfolders recursively'
        }
    };

    function updateStatsLabels() {
        const dict = uiStrings[currentLang];
        if (selectedMode === 'move') {
            statCopiedLabel.textContent = currentLang === 'ja' ? '移動済/予定' : 'Moved';
        } else {
            statCopiedLabel.textContent = currentLang === 'ja' ? 'コピー済/予定' : 'Copied';
        }
    }

    function setLanguage(lang) {
        currentLang = lang;
        if (lang === 'ja') {
            btnLangJa.classList.add('active');
            btnLangEn.classList.remove('active');
        } else {
            btnLangEn.classList.add('active');
            btnLangJa.classList.remove('active');
        }
        
        const dict = uiStrings[lang];
        
        // Update texts
        document.getElementById('subtitle-text').textContent = dict['subtitle-text'];
        document.querySelector('.setup-card .card-header h2').innerHTML = `<i class="fa-solid fa-sliders"></i> ${dict['setup-title']}`;

        document.getElementById('lbl-profile').innerHTML = `<i class="fa-solid fa-user-gear"></i> ${dict['lbl-profile']}`;
        // The save/save-as buttons briefly swap to an icon-only checkmark after a
        // click (see flashButtonSuccess), so their text spans may not exist yet.
        const profileSaveTextEl = document.getElementById('btn-profile-save-text');
        if (profileSaveTextEl) profileSaveTextEl.textContent = dict['btn-profile-save'];
        const profileSaveAsTextEl = document.getElementById('btn-profile-save-as-text');
        if (profileSaveAsTextEl) profileSaveAsTextEl.textContent = dict['btn-profile-save-as'];
        btnProfileSave.title = dict['btn-profile-save-title'];
        btnProfileSaveAs.title = dict['btn-profile-save-as-title'];
        btnProfileDelete.title = dict['btn-profile-delete-title'];

        document.getElementById('lbl-dst-dir').innerHTML = `<i class="fa-solid fa-folder-tree"></i> ${dict['lbl-dst-dir']}`;
        dstDirInput.placeholder = dict['placeholder-dst'];
        document.getElementById('lbl-mode').innerHTML = `<i class="fa-solid fa-gears"></i> ${dict['lbl-mode']}`;
        
        const toggleCopy = document.querySelector('.toggle-option[data-value="copy"]');
        toggleCopy.innerHTML = `<i class="fa-regular fa-copy"></i> ${dict['lbl-copy']}`;
        const toggleMove = document.querySelector('.toggle-option[data-value="move"]');
        toggleMove.innerHTML = `<i class="fa-solid fa-arrows-turn-to-dots"></i> ${dict['lbl-move']}`;
        
        document.getElementById('lbl-naming-rule').innerHTML = `<i class="fa-solid fa-signature"></i> ${dict['lbl-naming-rule']}`;
        document.getElementById('opt-custom-template').textContent = dict['opt-custom-template'];
        document.getElementById('lbl-custom-template').textContent = dict['lbl-custom-template'];
        document.getElementById('text-custom-tokens').textContent = dict['text-custom-tokens'];
        
        document.getElementById('lbl-advanced-filters').innerHTML = `<i class="fa-solid fa-sliders"></i> ${dict['lbl-advanced-filters']}`;
        document.getElementById('lbl-filter-extensions').textContent = dict['lbl-filter-extensions'];
        document.getElementById('lbl-recursive').textContent = dict['lbl-recursive'];
        document.getElementById('lbl-filter-date').textContent = dict['lbl-filter-date'];
        
        btnDryRun.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${dict['btn-dryrun-text']}`;
        btnStart.innerHTML = `<i class="fa-solid fa-circle-play"></i> ${dict['btn-start-text']}`;
        
        document.querySelector('#preview-card .card-header h2').innerHTML = `<i class="fa-solid fa-eye"></i> ${dict['preview-title-text']}`;
        document.querySelector('.preview-desc').textContent = dict['preview-desc-text'];
        
        document.querySelector('.status-label').textContent = dict['lbl-processing-file'];
        
        // Update stats labels
        const statBoxes = document.querySelectorAll('.stat-box');
        statBoxes[0].querySelector('.stat-label').textContent = dict['lbl-total-files'];
        statBoxes[2].querySelector('.stat-label').textContent = dict['lbl-skipped-files'];
        statBoxes[3].querySelector('.stat-label').textContent = dict['lbl-error-files'];
        updateStatsLabels();
        
        document.getElementById('title-log').textContent = dict['title-log'];
        document.getElementById('lbl-undo').textContent = dict['lbl-undo'];
        btnClearLog.textContent = dict['btn-clear'];
        
        // Update existing input placeholders
        const srcInputs = srcDirsContainer.querySelectorAll('.src-dir-input');
        srcInputs.forEach(input => input.placeholder = dict['placeholder-src']);
        const srcLabel = document.getElementById('lbl-src-dirs');
        if (srcLabel) {
            srcLabel.innerHTML = `<i class="fa-regular fa-folder-open"></i> ${dict['lbl-src-dirs']}`;
        }
        btnAddSrc.innerHTML = `<i class="fa-solid fa-plus"></i> ${dict['btn-add-src']}`;
        
        const selectButtons = document.querySelectorAll('.btn-select-src, #btn-select-dst');
        selectButtons.forEach(btn => {
            const isSelect = btn.classList.contains('btn-select-src') || btn.id === 'btn-select-dst';
            if (isSelect) {
                btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> ${dict['btn-select']}`;
            }
        });

        // Report card
        document.getElementById('title-report').textContent = dict['title-report'];
        document.getElementById('lbl-refresh-report').textContent = dict['lbl-refresh-report'];
        document.getElementById('text-report-empty').textContent = dict['text-report-empty'];
        document.getElementById('lbl-report-sessions').textContent = dict['lbl-report-sessions'];
        document.getElementById('lbl-report-total-files').textContent = dict['lbl-report-total-files'];
        document.getElementById('lbl-report-copy-files').textContent = dict['lbl-report-copy-files'];
        document.getElementById('lbl-report-move-files').textContent = dict['lbl-report-move-files'];
        document.getElementById('lbl-report-total-size').textContent = dict['lbl-report-total-size'];
        document.getElementById('lbl-legend-copy').textContent = dict['lbl-legend-copy'];
        document.getElementById('lbl-legend-move').textContent = dict['lbl-legend-move'];
        // Re-render the monthly breakdown so its inline copy/move labels follow the new language
        if (lastReportData) renderReport(lastReportData);
    }

    btnLangJa.addEventListener('click', () => { setLanguage('ja'); saveSettings(); });
    btnLangEn.addEventListener('click', () => { setLanguage('en'); saveSettings(); });

    // Applies a saved settings object (one profile's worth) onto the form.
    // Used both for the initial page load and whenever the user switches profiles.
    function applySettingsToForm(s) {
        if (!s) return;
        try {
            // Restore language first so placeholders render correctly
            if (s.language) setLanguage(s.language);

            // Reset source directory rows down to a single blank row before restoring
            const existingRows = srcDirsContainer.querySelectorAll('.src-dir-row');
            existingRows.forEach((row, idx) => { if (idx > 0) row.remove(); });
            const firstInput = srcDirsContainer.querySelector('.src-dir-input');
            if (firstInput) firstInput.value = '';

            if (Array.isArray(s.srcDirs) && s.srcDirs.length > 0) {
                s.srcDirs.forEach((dir, idx) => {
                    if (idx === 0) {
                        const rows = srcDirsContainer.querySelectorAll('.src-dir-row');
                        const input = rows[0] && rows[0].querySelector('.src-dir-input');
                        if (input) input.value = dir;
                    } else if (dir) {
                        btnAddSrc.click();
                        const allRows = srcDirsContainer.querySelectorAll('.src-dir-row');
                        const input = allRows[allRows.length - 1].querySelector('.src-dir-input');
                        if (input) input.value = dir;
                    }
                });
            }
            updateRemoveButtonsVisibility();

            dstDirInput.value = s.dstDir || '';

            const namingSelect = document.getElementById('naming-rule');
            namingSelect.value = s.namingRule || 'YYYY-MM-DD';
            const customGroup = document.getElementById('custom-template-group');
            if (namingSelect.value === 'custom') {
                customGroup.classList.remove('hidden');
                document.getElementById('custom-template').value = s.customTemplate || '';
            } else {
                customGroup.classList.add('hidden');
            }

            document.querySelectorAll('input[name="extensions"]').forEach(cb => {
                cb.checked = Array.isArray(s.extensions) && s.extensions.includes(cb.value);
            });

            document.getElementById('date-start').value = s.dateStart || '';
            document.getElementById('date-end').value = s.dateEnd || '';

            const recursiveEl = document.getElementById('recursive-scan');
            if (recursiveEl) recursiveEl.checked = !!s.recursive;

            // Apply mode last: the toggle's click handler also calls saveSettings(),
            // so by the time it fires the rest of the form already reflects this profile.
            const targetMode = s.mode || 'copy';
            toggleOptions.forEach(opt => {
                if (opt.getAttribute('data-value') === targetMode) {
                    opt.click();
                }
            });
        } catch (e) { /* corrupt profile data — ignore */ }
    }

    function populateProfileSelect(store) {
        profileSelect.innerHTML = '';
        store.profiles.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = p.name;
            profileSelect.appendChild(opt);
        });
        profileSelect.value = store.activeProfile;
    }

    function switchProfile(name) {
        const store = loadProfilesStore();
        if (!store) return;
        const profile = store.profiles.find(p => p.name === name);
        if (!profile) return;
        store.activeProfile = name;
        saveProfilesStore(store);
        applySettingsToForm(profile.settings);
    }

    function flashButtonSuccess(btn) {
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-check"></i>';
        setTimeout(() => {
            btn.innerHTML = original;
            btn.disabled = false;
        }, 1200);
    }

    profileSelect.addEventListener('change', () => {
        switchProfile(profileSelect.value);
    });

    btnProfileSave.addEventListener('click', () => {
        saveSettings();
        flashButtonSuccess(btnProfileSave);
    });

    btnProfileSaveAs.addEventListener('click', async () => {
        const dict = uiStrings[currentLang];
        const cancelLbl = currentLang === 'ja' ? 'キャンセル' : 'Cancel';
        const name = await showPrompt(dict['prompt-profile-name'], '', cancelLbl);
        if (!name) return;

        const store = loadProfilesStore() || migrateLegacySettingsIfNeeded();
        const existingIdx = store.profiles.findIndex(p => p.name === name);
        if (existingIdx !== -1) {
            const overwriteMsg = dict['confirm-profile-overwrite'].replace('{name}', name);
            if (!await showConfirm(overwriteMsg, cancelLbl)) return;
            store.profiles[existingIdx].settings = getCurrentFormSettings();
        } else {
            store.profiles.push({ name, settings: getCurrentFormSettings() });
        }
        store.activeProfile = name;
        saveProfilesStore(store);
        populateProfileSelect(store);
        flashButtonSuccess(btnProfileSaveAs);
    });

    btnProfileDelete.addEventListener('click', async () => {
        const dict = uiStrings[currentLang];
        const cancelLbl = currentLang === 'ja' ? 'キャンセル' : 'Cancel';
        const store = loadProfilesStore();
        if (!store) return;

        if (store.profiles.length <= 1) {
            await showAlert(dict['error-profile-last']);
            return;
        }

        const name = store.activeProfile;
        const confirmMsg = dict['confirm-profile-delete'].replace('{name}', name);
        if (!await showConfirm(confirmMsg, cancelLbl)) return;

        store.profiles = store.profiles.filter(p => p.name !== name);
        store.activeProfile = store.profiles[0].name;
        saveProfilesStore(store);
        populateProfileSelect(store);
        applySettingsToForm(store.profiles[0].settings);
    });

    function initProfiles() {
        const store = migrateLegacySettingsIfNeeded();
        populateProfileSelect(store);
        const active = store.profiles.find(p => p.name === store.activeProfile) || store.profiles[0];
        if (active) applySettingsToForm(active.settings);
    }

    initProfiles();
    loadReport();
});
