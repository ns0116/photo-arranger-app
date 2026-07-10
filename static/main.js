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

    // Current app state
    let selectedMode = 'copy'; // Default mode
    let simulationResults = [];
    let currentLang = 'ja';

    // Toggle mode buttons
    const toggleOptions = document.querySelectorAll('.toggle-option');
    toggleOptions.forEach(option => {
        option.addEventListener('click', () => {
            toggleOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
            selectedMode = option.getAttribute('data-value');
            
            // UIラベル更新
            updateStatsLabels();
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
        if (!confirm(confirmMsg)) {
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
            alert(uiStrings[currentLang]['error-select-dirs']);
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
                    lang: currentLang
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
            alert(`エラーが発生しました: ${error.message}`);
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
        previewCount.textContent = `${simulationResults.length} ${currentLang === 'ja' ? '件' : 'items'}`;
        previewList.innerHTML = '';

        simulationResults.forEach(item => {
            const row = document.createElement('div');
            const displayAction = item.action || 'copy';
            row.className = `preview-row ${displayAction}-row`;

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
            row.innerHTML = `
                <div class="preview-file" title="${fileDisplay}">
                    ${fileDisplay}
                </div>
                <div class="preview-details">
                    <span class="p-badge ${escapeHtml(badgeClass)}">${escapeHtml(badgeText)}</span>
                    <i class="fa-solid fa-arrow-right-long preview-arrow"></i>
                    <span class="preview-dest-folder" title="${destEscaped}">${destEscaped}</span>
                </div>
            `;
            previewList.appendChild(row);
        });
    }

    // Undo click event handler
    btnUndo.addEventListener('click', async () => {
        const confirmMsg = currentLang === 'ja'
            ? '最新の整理セッションを元に戻しますか？（コピーされたファイルは削除され、移動されたファイルは元のフォルダに戻ります）'
            : 'Rollback the latest session? (Copied files will be deleted, and moved files will be returned to their original folders)';
        if (!confirm(confirmMsg)) return;

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
            alert(data.message);
            btnUndo.classList.add('hidden'); // Hide undo button after rollback succeeds
        } catch (error) {
            console.error('Undo request failed:', error);
            addLog(`${currentLang === 'ja' ? 'Undo失敗' : 'Undo failed'}: ${error.message}`, 'error');
            alert(`${currentLang === 'ja' ? 'Undoエラー' : 'Undo error'}: ${error.message}`);
        } finally {
            btnUndo.disabled = false;
            btnUndo.innerHTML = `<i class="fa-solid fa-rotate-left"></i> ${uiStrings[currentLang]['lbl-undo']}`;
        }
    });

    // i18n dynamic elements maps
    const btnLangJa = document.getElementById('btn-lang-ja');
    const btnLangEn = document.getElementById('btn-lang-en');

    const uiStrings = {
        ja: {
            'subtitle-text': 'EXIF撮影日時とファイル更新日時を自動解析して写真を整理します',
            'setup-title': '設定',
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
            'shutdown-desc-screen': 'ブラウザのタブを閉じて問題ありません。'
        },
        en: {
            'subtitle-text': 'Automatically organize photos into date folders using EXIF metadata and file mtimes',
            'setup-title': 'Settings',
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
            'shutdown-desc-screen': 'You can safely close this browser tab.'
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
        document.querySelector('label[for="dst-dir"]').innerHTML = `<i class="fa-solid fa-folder-open"></i> ${dict['lbl-dst-dir']}`;
        dstDirInput.placeholder = dict['placeholder-dst'];
        document.querySelector('.form-group label:not([for])').innerHTML = `<i class="fa-solid fa-gears"></i> ${dict['lbl-mode']}`;
        
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
        const srcLabels = document.querySelector('.setup-card .form-group label');
        srcLabels.innerHTML = `<i class="fa-regular fa-folder-open"></i> ${dict['lbl-src-dirs']}`;
        btnAddSrc.innerHTML = `<i class="fa-solid fa-plus"></i> ${dict['btn-add-src']}`;
        
        const selectButtons = document.querySelectorAll('.btn-select-src, #btn-select-dst');
        selectButtons.forEach(btn => {
            const isSelect = btn.classList.contains('btn-select-src') || btn.id === 'btn-select-dst';
            if (isSelect) {
                btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> ${dict['btn-select']}`;
            }
        });
    }

    btnLangJa.addEventListener('click', () => setLanguage('ja'));
    btnLangEn.addEventListener('click', () => setLanguage('en'));
});
