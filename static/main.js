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

    // Current app state
    let selectedMode = 'copy'; // Default mode
    let simulationResults = [];

    // Toggle mode buttons
    const toggleOptions = document.querySelectorAll('.toggle-option');
    toggleOptions.forEach(option => {
        option.addEventListener('click', () => {
            toggleOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
            selectedMode = option.getAttribute('data-value');
            
            // UIラベル更新
            if (selectedMode === 'move') {
                statCopiedLabel.textContent = '移動済/予定';
            } else {
                statCopiedLabel.textContent = 'コピー済/予定';
            }
        });
    });

    // Folder selection helper
    async function selectDirectory(targetInput) {
        try {
            targetInput.disabled = true;
            const response = await fetch('/api/select-dir', { method: 'POST' });
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
            <input type="text" class="src-dir-input" placeholder="整理する写真が入っているフォルダのパス" spellcheck="false">
            <button type="button" class="btn btn-secondary btn-select-src">
                <i class="fa-solid fa-magnifying-glass"></i> 選択
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
            btnCancel.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 中断中...`;
            const response = await fetch('/api/cancel', { method: 'POST' });
            const data = await response.json();
            addLog(data.message, 'info');
        } catch (error) {
            console.error('Cancel request failed:', error);
            addLog('中断シグナルの送信に失敗しました。', 'error');
            btnCancel.disabled = false;
            btnCancel.innerHTML = `<i class="fa-solid fa-hand"></i> 中断`;
        }
    });

    // Shutdown backend server
    btnShutdown.addEventListener('click', async () => {
        if (!confirm('サーバーをシャットダウンしますか？終了すると再度起動するまでアプリは利用できなくなります。')) {
            return;
        }

        try {
            addLog('サーバーのシャットダウン要求を送信しました...', 'error');
            const response = await fetch('/api/shutdown', { method: 'POST' });
            const data = await response.json();
            
            document.body.innerHTML = `
                <div style="display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:100vh;color:#f3f4f6;background-color:#080b11;font-family:sans-serif;text-align:center;padding:2rem;">
                    <i class="fa-solid fa-power-off" style="font-size:4rem;color:#ef4444;margin-bottom:1.5rem;text-shadow:0 0 20px rgba(239,68,68,0.4)"></i>
                    <h1 style="font-size:1.8rem;margin-bottom:1rem;">サーバーを終了しました</h1>
                    <p style="color:#9ca3af;font-size:1rem;">ブラウザのタブを閉じて問題ありません。</p>
                </div>
            `;
        } catch (error) {
            // シャットダウン成功時は接続切断でエラーになることがあるため、強制的に終了画面を表示
            document.body.innerHTML = `
                <div style="display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:100vh;color:#f3f4f6;background-color:#080b11;font-family:sans-serif;text-align:center;padding:2rem;">
                    <i class="fa-solid fa-power-off" style="font-size:4rem;color:#ef4444;margin-bottom:1.5rem;text-shadow:0 0 20px rgba(239,68,68,0.4)"></i>
                    <h1 style="font-size:1.8rem;margin-bottom:1rem;">サーバーを終了しました</h1>
                    <p style="color:#9ca3af;font-size:1rem;">ブラウザのタブを閉じて問題ありません。</p>
                </div>
            `;
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

    // Trigger dry-run or actual run
    btnDryRun.addEventListener('click', () => startProcessing(true));
    btnStart.addEventListener('click', () => startProcessing(false));

    async function startProcessing(dryRun = false) {
        const srcDirInputs = srcDirsContainer.querySelectorAll('.src-dir-input');
        const srcDirs = Array.from(srcDirInputs).map(input => input.value.trim()).filter(path => path !== '');
        const dstDir = dstDirInput.value.trim();
        const namingRule = namingRuleSelect.value;

        if (srcDirs.length === 0 || !dstDir) {
            alert('コピー元とコピー先のディレクトリを指定してください。');
            return;
        }

        // Reset UI state
        progressCard.classList.remove('hidden');
        logCard.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        currentFilename.textContent = 'スキャン中...';
        
        // Reset cancel button
        btnCancel.disabled = false;
        btnCancel.innerHTML = `<i class="fa-solid fa-hand"></i> 中断`;
        if (dryRun) {
            btnCancel.classList.add('hidden'); // シミュレーションは一瞬またはI/Oなしなので中断不要
            progressTitle.textContent = 'シミュレーション中';
        } else {
            btnCancel.classList.remove('hidden');
            progressTitle.textContent = '実行中';
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
            addLog('シミュレーション（Dry Run）を開始します...', 'info');
        } else {
            addLog(`整理処理 (${selectedMode === 'move' ? '移動' : 'コピー'}モード) を開始します...`, 'info');
        }

        setControlsDisabled(true);

        try {
            const response = await fetch('/api/arrange', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    src_dirs: srcDirs, 
                    dst_dir: dstDir, 
                    naming_rule: namingRule,
                    mode: selectedMode,
                    dry_run: dryRun
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
                progressTitle.textContent = dryRun ? 'シミュレーション完了' : '処理完了';
            } else {
                progressIcon.className = 'fa-solid fa-circle-exclamation';
                progressIcon.style.color = 'var(--danger)';
                progressTitle.textContent = '処理中断';
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
            let type = 'info';
            if (data.message.includes('コピー成功:') || data.message.includes('移動成功:') || data.message.startsWith('新規')) {
                type = 'success';
            } else if (data.message.includes('スキップ')) {
                type = 'skip';
            } else if (data.message.includes('エラー:')) {
                type = 'error';
            } else if (data.message.includes('衝突')) {
                type = 'rename'; // Custom type for styling
            }
            addLog(data.message, type);
        }

        // Collect simulation rows for preview
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
            currentFilename.textContent = '完了しました。';
        }
        
        if (data.status === 'cancelled') {
            addLog(data.message, 'error');
            currentFilename.textContent = '中断されました。';
            progressIcon.className = 'fa-solid fa-circle-exclamation';
            progressIcon.style.color = 'var(--danger)';
            progressTitle.textContent = '処理中断';
        }
    }

    // Render Dry Run preview list
    function renderSimulationPreview() {
        previewCard.classList.remove('hidden');
        previewCount.textContent = `${simulationResults.length} 件`;
        previewList.innerHTML = '';

        simulationResults.forEach(item => {
            const row = document.createElement('div');
            // item.action can be: copy, move, skip, rename, rename_move, error
            const displayAction = item.action || 'copy';
            row.className = `preview-row ${displayAction}-row`;

            const badgeTextMap = {
                'copy': 'コピー',
                'move': '移動',
                'skip': 'スキップ',
                'rename': 'リネーム',
                'rename_move': '名変移動',
                'error': 'エラー'
            };
            const badgeClass = item.action || 'copy';
            const badgeText = badgeTextMap[badgeClass] || 'コピー';

            // Show name transition for rename actions
            const targetFilename = item.target || item.filename;
            const destDisplay = item.action.startsWith('rename') 
                ? `${item.folder}/${targetFilename}` 
                : `${item.folder}/`;

            row.innerHTML = `
                <div class="preview-file" title="${item.src_dir}/${item.filename}">
                    ${item.src_dir}/${item.filename}
                </div>
                <div class="preview-details">
                    <span class="p-badge ${badgeClass}">${badgeText}</span>
                    <i class="fa-solid fa-arrow-right-long preview-arrow"></i>
                    <span class="preview-dest-folder" title="${destDisplay}">${destDisplay}</span>
                </div>
            `;
            previewList.appendChild(row);
        });
    }
});
