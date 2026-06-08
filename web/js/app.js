let currentAspectRatio = 1;  // 当前图片的宽高比

// Tab Switching Logic
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        const prevTab = document.querySelector('.nav-item.active');
        const prevId = prevTab ? prevTab.dataset.tab : '';

        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');

        // 嵌入式浏览器（AI 聊天）管理
        const target = btn.dataset.tab;
        if (target === 'aichat') {
            const firstTab = document.querySelector('#aichat-tabs .sub-nav-item.active');
            if (firstTab) {
                const url = firstTab.dataset.url;
                const tabId = firstTab.textContent.trim();
                pywebview.api.embed_browser_show_tab(tabId, url);
            }
        } else if (prevId === 'aichat') {
            pywebview.api.embed_browser_hide();
        }

        // 终端管理
        const content = document.querySelector('.content');
        if (target === 'terminal') {
            if (content) { content.style.overflowY = 'hidden'; content.style.padding = '0'; }
            if (typeof initTerminal === 'function') initTerminal();
        } else {
            if (content) { content.style.overflowY = ''; content.style.padding = ''; }
        }
    });
});

document.querySelectorAll('.sub-nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        const parent = btn.closest('.card');
        parent.querySelectorAll('.sub-nav-item').forEach(b => b.classList.remove('active'));
        parent.querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.sub).classList.add('active');
    });
});

// Custom Alert System
function showAlert(message) {
    document.getElementById('modal-message').textContent = message;
    document.getElementById('modal-overlay').classList.add('show');
}

function hideAlert() {
    document.getElementById('modal-overlay').classList.remove('show');
}

// Helper Functions
async function selectFile(id, fileTypes = null) {
    const res = await pywebview.api.select_file(['Image files (*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.ico;*.heic;*.heif;*.tiff;*.tif;*.gif)', 'All files (*.*)']);
    if (res.success && res.data) {
        document.getElementById(id).value = res.data;
        if (id === 'img-size-src') {
            const infoRes = await pywebview.api.get_image_info(res.data);
            if (infoRes.success) {
                document.getElementById('img-width').value = infoRes.data.width;
                document.getElementById('img-height').value = infoRes.data.height;
                currentAspectRatio = infoRes.data.width / infoRes.data.height;
            }
        }
    } else if (!res.success && res.error !== 'Cancelled') {
        showAlert(res.error);
    }
}

async function loadBase64File() {
    // 1. 先选择文件（不触发禁用状态）
    const selRes = await pywebview.api.select_file(['Text files (*.txt)', 'All files (*.*)']);
    if (!selRes.success) {
        if (selRes.error !== 'Cancelled') showAlert(selRes.error);
        return;
    }
    const filePath = selRes.data;

    // 2. 选择返回后，设置按钮为读取中并禁用
    const btn = document.getElementById('btn-load-b64');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '读取中...';
    
    try {
        // 3. 执行实际的读取操作
        const res = await pywebview.api.read_file_content_api(filePath);
        if (res.success) {
            document.getElementById('b64-input').value = res.data;
        } else {
            showAlert(res.error);
        }
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function copyToClipboard(id) {
    const val = document.getElementById(id).value;
    if (val) {
        navigator.clipboard.writeText(val);
        showToast('已复制到剪贴板');
    }
}

async function copyValue(id) {
    const val = document.getElementById(id).value;
    if (val) {
        navigator.clipboard.writeText(val);
        showToast('已复制到剪贴板');
    }
}

function showToast(message) {
    const container = document.getElementById('toast-container');
    const text = document.getElementById('toast-text');
    text.textContent = message;
    
    if (window.toastTimeout) clearTimeout(window.toastTimeout);
    
    container.classList.add('show');
    
    window.toastTimeout = setTimeout(() => {
        container.classList.remove('show');
    }, 2000);
}

function toggleCase(id) {
    const el = document.getElementById(id);
    const val = el.value;
    el.value = val === val.toUpperCase() ? val.toLowerCase() : val.toUpperCase();
}

// Translate Tools
async function doTranslate() {
    const text = document.getElementById('translate-input').value;
    if (!text) { showAlert('请输入待翻译文本'); return; }
    const source = document.getElementById('translate-source-lang').value;
    const target = document.getElementById('translate-target-lang').value;

    const btn = document.getElementById('translate-btn');
    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '翻译中...';

    try {
        const res = await pywebview.api.translate(text, source, target);
        if (res.success) {
            document.getElementById('translate-output').value = res.data.translated;
        } else {
            showAlert(res.error);
        }
    } finally {
        btn.disabled = false;
        btn.textContent = oldText;
    }
}

function swapTranslateLangs() {
    const src = document.getElementById('translate-source-lang');
    const tgt = document.getElementById('translate-target-lang');
    if (src.value === 'auto') return;  // 自动检测无法交换
    const tmp = src.value;
    src.value = tgt.value;
    tgt.value = tmp;
}

function clearTranslate() {
    document.getElementById('translate-input').value = '';
    document.getElementById('translate-output').value = '';
}

// Hash Tools
async function calcHash(algo, isHmac = false) {
    const isFileMode = document.querySelector('[data-sub="hash-file"]').classList.contains('active');
    const key = document.getElementById('hash-key').value;
    let res;
    if (isFileMode) {
        const path = document.getElementById('hash-file-path').value;
        if (!path) { showAlert('请先选择文件'); return; }
        res = await pywebview.api.calc_file_hash(path, algo, isHmac, key);
    } else {
        const data = document.getElementById('hash-input').value;
        if (!data) return;
        res = await pywebview.api.calc_hash(data, algo, isHmac, key);
    }
    if (res.success) {
        document.getElementById('hash-output').value = res.data;
    } else {
        showAlert(res.error);
    }
}

function clearHash() {
    document.getElementById('hash-input').value = '';
    document.getElementById('hash-file-path').value = '';
    document.getElementById('hash-key').value = '';
    document.getElementById('hash-output').value = '';
}

// Crypto Tools
// ---- 加密解密：获取当前算法标签下的配置 ----
function getCryptoAlgoTab() {
    // 返回当前激活的算法子标签名称
    const tabs = ['crypto-algo-aes', 'crypto-algo-des', 'crypto-algo-rc2',
                  'crypto-algo-rc4', 'crypto-algo-rc5',
                  'crypto-algo-rc6', 'crypto-algo-chacha20',
                  'crypto-algo-rabbit', 'crypto-algo-xor'];
    for (const id of tabs) {
        if (document.getElementById(id).classList.contains('active')) return id;
    }
    return 'crypto-algo-aes';
}

function getCryptoConfig() {
    const tab = getCryptoAlgoTab();
    if (tab === 'crypto-algo-aes') {
        return {
            algorithm: document.getElementById('crypto-aes-variant').value,
            mode: document.getElementById('crypto-aes-mode').value,
            padding: document.getElementById('crypto-aes-padding').value,
        };
    }
    if (tab === 'crypto-algo-des') {
        return {
            algorithm: document.getElementById('crypto-des-variant').value,
            mode: document.getElementById('crypto-des-mode').value,
            padding: document.getElementById('crypto-des-padding').value,
        };
    }
    if (tab === 'crypto-algo-rc2') {
        return {
            algorithm: 'RC2',
            mode: document.getElementById('crypto-rc2-mode').value,
            padding: document.getElementById('crypto-rc2-padding').value,
        };
    }
    if (tab === 'crypto-algo-rc5') {
        return {
            algorithm: 'RC5',
            mode: document.getElementById('crypto-rc5-mode').value,
            padding: document.getElementById('crypto-rc5-padding').value,
        };
    }
    if (tab === 'crypto-algo-rc6') {
        return {
            algorithm: 'RC6',
            mode: document.getElementById('crypto-rc6-mode').value,
            padding: document.getElementById('crypto-rc6-padding').value,
        };
    }
    // 流密码：无需模式和填充
    const algoMap = {
        'crypto-algo-rc4': 'RC4',
        'crypto-algo-chacha20': 'ChaCha20',
        'crypto-algo-rabbit': 'Rabbit',
        'crypto-algo-xor': 'XOR',
    };
    return { algorithm: algoMap[tab] || 'RC4', mode: '', padding: 'none' };
}

function getCryptoKeyIvSizes() {
    const cfg = getCryptoConfig();
    const algo = cfg.algorithm;
    if (algo.startsWith('AES-')) return { key: parseInt(algo.split('-')[1]) / 8, iv: 16 };
    if (algo === 'DES') return { key: 8, iv: 8 };
    if (algo === '3DES') return { key: 24, iv: 8 };
    if (algo === 'RC2') return { key: 16, iv: 8 };
    if (algo === 'RC5') return { key: 16, iv: 8 };
    if (algo === 'RC6') return { key: 16, iv: 16 };
    if (algo === 'ChaCha20') return { key: 32, iv: 8 };
    if (algo === 'Rabbit') return { key: 16, iv: 8 };
    // RC4, XOR: variable
    return { key: 16, iv: 0 };
}

function onCryptoCfgChange() {
    const cfg = getCryptoConfig();
    const sizes = getCryptoKeyIvSizes();
    const mode = cfg.mode;
    const ivGroup = document.getElementById('crypto-iv-group');
    const ivInput = document.getElementById('crypto-iv');
    const keyInput = document.getElementById('crypto-key');

    // 清空密钥和 IV
    keyInput.value = '';
    document.getElementById('crypto-iv').value = '';

    // 密钥长度提示
    keyInput.placeholder = `十六进制密钥 (${sizes.key} 字节 / ${sizes.key * 2} 个十六进制字符)`;

    // IV 显示/隐藏
    const needsIV = mode !== 'ECB' && sizes.iv > 0;
    if (needsIV) {
        ivGroup.style.display = 'flex';
        ivInput.placeholder = `十六进制 IV (${sizes.iv} 字节 / ${sizes.iv * 2} 个十六进制字符)`;
    } else {
        ivGroup.style.display = 'none';
    }

    // 流密码无模式时，隐藏 IV（RC4 不需要 IV，XOR 不需要 IV）
    if (!mode) {
        if (cfg.algorithm === 'RC4' || cfg.algorithm === 'XOR') {
            ivGroup.style.display = 'none';
        } else if (cfg.algorithm === 'ChaCha20') {
            ivGroup.style.display = 'flex';
            ivInput.placeholder = '十六进制 Nonce (8 字节 / 16 个十六进制字符)';
        } else if (cfg.algorithm === 'Rabbit') {
            ivGroup.style.display = 'flex';
            ivInput.placeholder = '十六进制 IV (8 字节 / 16 个十六进制字符，可选)';
        }
    }

    // 填充选择：流模式 CTR 自动用 None 并禁用
    const algoTab = getCryptoAlgoTab();
    let paddingId;
    if (algoTab === 'crypto-algo-aes') paddingId = 'crypto-aes-padding';
    else if (algoTab === 'crypto-algo-des') paddingId = 'crypto-des-padding';
    else if (algoTab === 'crypto-algo-rc2') paddingId = 'crypto-rc2-padding';
    else if (algoTab === 'crypto-algo-rc5') paddingId = 'crypto-rc5-padding';
    else if (algoTab === 'crypto-algo-rc6') paddingId = 'crypto-rc6-padding';
    else paddingId = null;
    const paddingSelect = document.getElementById(paddingId);
    if (paddingSelect) {
        if (['CTR', 'GCM'].includes(mode)) {
            paddingSelect.value = 'none';
            paddingSelect.disabled = true;
            paddingSelect.style.opacity = '0.4';
        } else {
            paddingSelect.disabled = false;
            paddingSelect.style.opacity = '';
            if (paddingSelect.value === 'none') paddingSelect.value = 'pkcs7';
        }
    }

    updateCryptoFileModeUI();
}

function updateCryptoAlgoTabUI() {
    // 算法子标签切换时：清空密钥和 IV，更新提示
    document.getElementById('crypto-key').value = '';
    document.getElementById('crypto-iv').value = '';
    onCryptoCfgChange();
}

function updateCryptoFileModeUI() {
    const isFileMode = document.querySelector('[data-sub="crypto-file"]').classList.contains('active');
    document.getElementById('crypto-in-fmt-wrap').style.display = isFileMode ? 'none' : 'flex';
    document.getElementById('crypto-out-fmt-wrap').style.display = isFileMode ? 'none' : 'flex';
    document.getElementById('crypto-result-card').style.display = isFileMode ? 'none' : '';
}

async function selectCryptoFile() {
    const res = await pywebview.api.select_file(['All files (*.*)']);
    if (res.success && res.data) {
        document.getElementById('crypto-file-path').value = res.data;
    } else if (!res.success && res.error !== 'Cancelled') {
        showAlert(res.error);
    }
}

async function cryptoOperation(action) {
    const cfg = getCryptoConfig();
    const isFileMode = document.querySelector('[data-sub="crypto-file"]').classList.contains('active');
    const key = document.getElementById('crypto-key').value.trim();
    const iv = document.getElementById('crypto-iv').value.trim();
    const algo = cfg.algorithm;
    const mode = cfg.mode;
    const padding = cfg.padding;

    if (!key) { showAlert('请输入密钥'); return; }
    if (mode && mode !== 'ECB' && !iv) { showAlert('当前模式需要填写 IV'); return; }
    // 流密码 ChaCha20 需要 nonce
    if (!mode && algo === 'ChaCha20' && !iv) { showAlert('ChaCha20 需要填写 Nonce'); return; }

    if (isFileMode) {
        const filePath = document.getElementById('crypto-file-path').value;
        if (!filePath) { showAlert('请先选择文件'); return; }
        const res = await pywebview.api.crypto_file(filePath, algo, mode, key, iv, action, padding);
        if (res.success) {
            showToast('文件保存成功');
        } else if (res.error !== '已取消') {
            showAlert(res.error);
        }
        return;
    }

    const data = document.getElementById('crypto-input').value;
    if (!data) { showAlert('请输入文本'); return; }

    const inFmt = document.getElementById('crypto-in-fmt').value;
    const outFmt = document.getElementById('crypto-out-fmt').value;
    const res = await pywebview.api.crypto_symmetric(data, algo, mode, key, iv, action, inFmt, outFmt, padding);
    if (res.success) {
        document.getElementById('crypto-output').value = res.data;
    } else {
        showAlert(res.error);
    }
}

async function cryptoGenerateKey() {
    const size = getCryptoKeyIvSizes().key;
    const res = await pywebview.api.crypto_generate_bytes(size);
    if (res.success) {
        document.getElementById('crypto-key').value = res.data;
    } else {
        showAlert(res.error);
    }
}

async function cryptoGenerateIV() {
    const sizes = getCryptoKeyIvSizes();
    let size = sizes.iv;
    if (size === 0) size = 8;  // fallback
    const res = await pywebview.api.crypto_generate_bytes(size);
    if (res.success) {
        document.getElementById('crypto-iv').value = res.data;
    } else {
        showAlert(res.error);
    }
}

function clearCrypto() {
    document.getElementById('crypto-input').value = '';
    document.getElementById('crypto-file-path').value = '';
    document.getElementById('crypto-key').value = '';
    document.getElementById('crypto-iv').value = '';
    document.getElementById('crypto-output').value = '';
}

// Encode Tools
async function encodeDecode(action) {
    const data = document.getElementById('encode-input').value;
    if (!data) return;
    const res = await pywebview.api.encode_decode(data, action);
    if (res.success) {
        document.getElementById('encode-output').value = res.data;
    } else {
        showAlert(res.error);
    }
}

function clearEncode() {
    document.getElementById('encode-input').value = '';
    document.getElementById('encode-output').value = '';
}

// 使用动态导入
let wasmReady = null;      // 存储初始化 Promise
let wasmFormat = null;     // 存储格式化函数

/**
 * 加载 WASM 模块（只执行一次）
 *
 * lua_fmt 源码是用 npm install @wasm-fmt/lua_fmt 下载后复制过来的
 *
 * @returns {Promise<void>}
 */
async function loadWasm() {
    if (wasmReady) return wasmReady;

    // 动态导入：返回 Promise，不会阻塞顶层
    wasmReady = (async () => {
        try {
            // 动态导入 JS 包装器
            const module = await import('./lua_fmt/lua_fmt_web.js');
            const initAsync = module.default;
            wasmFormat = module.format;

            // 直接使用相对路径（相对于当前 HTML 文件）
            // 假设 lua_fmt_bg.wasm 与 lua_fmt_web.js 在同一目录下
            const wasmUrl = './js/lua_fmt/lua_fmt_bg.wasm';
            await initAsync(wasmUrl);
        } catch (err) {
            console.error('load WASM model fail:', err);
            throw new Error(`load WASM model fail: ${err.message || String(err)}`);
         }
    })();

    return wasmReady;
}

async function lua_format(data, options = {}) {
    // 等待 WASM 模块加载完成
    await loadWasm();

    // 默认配置（可根据需要调整）
    const defaultOptions = {
        column_width: 120,
        indent_width: 4,
        use_tabs: false,
    };

    const mergedOptions = { ...defaultOptions, ...options };

    try {
        const formatted = wasmFormat(data, mergedOptions);
        return { success: true, data: formatted };
    } catch (err) {
        let msg = err.message;
        if (msg == null || msg === "") {
            msg = "格式化失败，请检查 Lua 代码是否正确。";
        }
        return { success: false, error: msg };
     }
}

// Format Tools
async function formatData(type) {
    const isFileMode = document.querySelector('[data-sub="format-file"]').classList.contains('active');
    if (isFileMode) {
        showAlert('文件模式格式化暂未实现，请使用文本模式');
        return;
    }
    const data = document.getElementById('format-input').value;
    if (!data) return;

    const res = type === "lua_format"
        ? await lua_format(data)
        : await pywebview.api.format_data(data, type);

    if (res.success) {
        document.getElementById('format-output').value = res.data;
    } else {
        showAlert(res.error);
    }
}

function clearFormat() {
    document.getElementById('format-input').value = '';
    document.getElementById('format-output').value = '';
    document.getElementById('format-file-path').value = '';
}

// Base Conversion Tools
function getSelectedBase(name) {
    const radio = document.querySelector(`input[name="${name}"]:checked`);
    return radio ? radio.value : (name === 'base-from-radio' ? '10' : '16');
}

async function convertBase() {
    const data = document.getElementById('base-input').value.trim();
    const baseOutput = document.getElementById('base-output');
    
    if (!data) {
        baseOutput.value = '';
        return;
    }
    
    const fromBase = getSelectedBase('base-from-radio');
    const toBase = getSelectedBase('base-to-radio');
    
    const res = await pywebview.api.convert_base(data, fromBase, toBase);
    if (res.success) {
        baseOutput.value = res.data;
    } else {
        // Real-time conversion usually doesn't show alert for partial/invalid input
        baseOutput.value = '';
    }
}

function clearBase() {
    document.getElementById('base-input').value = '';
    document.getElementById('base-output').value = '';
}

function initBaseConvListeners() {
    const input = document.getElementById('base-input');
    if (!input) return;
    
    // Auto calculate on input
    input.addEventListener('input', convertBase);
    
    // Auto calculate when changing bases
    document.querySelectorAll('input[name="base-from-radio"], input[name="base-to-radio"]').forEach(radio => {
        radio.addEventListener('change', convertBase);
    });
}


function initPermissionSearch() {
    const androidInput = document.getElementById('android-perm-search');
    
    if (androidInput) androidInput.addEventListener('input', (e) => filterTable('android-perm-table', e.target.value));
    
}

function filterTable(tableId, query) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const rows = table.querySelectorAll('tbody tr');
    query = query.toLowerCase();
    rows.forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(query) ? '' : 'none';
    });
}


async function openDoc(platform) {
    const urls = {
        'android': 'https://developer.android.com/reference/android/Manifest.permission'
    };
    await pywebview.api.open_url(urls[platform]);
}

async function fetchPermissions(platform) {
    const btn = document.getElementById(platform + '-fetch-btn');
    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '正在获取...';
    
    try {
        const res = await pywebview.api.fetch_permissions(platform);
        if (res.success) {
            renderPermissions(platform, res.data);
            showToast('更新成功');
            if (platform === 'android') {
                document.getElementById('android-table-container').style.display = 'block';
            }
        } else {
            showAlert(res.error);
        }
    } finally {
        btn.disabled = false;
        btn.textContent = '更新权限';
    }
}

async function loadLocalPermissions() {
    const platforms = ['android'];
    for (const p of platforms) {
        const res = await pywebview.api.get_local_permissions(p);
        if (res.success && res.data) {
            renderPermissions(p, res.data);
            document.getElementById(p + '-fetch-btn').textContent = '更新权限';
            if (p === 'android') document.getElementById('android-table-container').style.display = 'block';
        } else {
            document.getElementById(p + '-fetch-btn').textContent = '获取权限';
            if (p === 'android') document.getElementById('android-table-container').style.display = 'none';
        }
    }
}

function renderPermissions(platform, data) {
    const tbody = document.getElementById(platform + '-perm-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    data.forEach(item => {
        const tr = document.createElement('tr');
        
        if (platform === 'android') {
            const tdName = document.createElement('td');
            tdName.textContent = item.name;
            tdName.style.fontWeight = 'bold';
            tdName.classList.add('truncate');
            tdName.dataset.tooltip = item.name;
            
            const tdAdded = document.createElement('td');
            tdAdded.textContent = item.added || '-';
            tdAdded.classList.add('text-center');
            
            const tdDeprecated = document.createElement('td');
            tdDeprecated.textContent = item.deprecated || '-';
            tdDeprecated.classList.add('text-center');
            
            const tdLevel = document.createElement('td');
            let levelText = item.permission_level || '-';
            tdLevel.textContent = levelText;
            tdLevel.classList.add('text-center');
            tdLevel.classList.add('truncate');
            tdLevel.dataset.tooltip = levelText;
            
            const tdDesc = document.createElement('td');
            tdDesc.textContent = item.desc || '-';
            
            tr.appendChild(tdName);
            tr.appendChild(tdAdded);
            tr.appendChild(tdDeprecated);
            tr.appendChild(tdLevel);
            tr.appendChild(tdDesc);
        } else {
            const tdName = document.createElement('td');
            tdName.textContent = item.name;
            tdName.style.fontWeight = 'bold';
            tdName.classList.add('truncate');
            tdName.dataset.tooltip = item.name;

            const tdAdded = document.createElement('td');
            tdAdded.textContent = item.added || '-';
            tdAdded.classList.add('text-center');

            const tdDeprecated = document.createElement('td');
            tdDeprecated.textContent = item.deprecated || '-';
            tdDeprecated.classList.add('text-center');

            const tdDesc = document.createElement('td');
            tdDesc.textContent = item.description || item.desc || '-';
            
            tr.appendChild(tdName);
            tr.appendChild(tdAdded);
            tr.appendChild(tdDeprecated);
            tr.appendChild(tdDesc);
        }
        tbody.appendChild(tr);
    });
}

// Time Tools
function initTimeZones() {
    const selects = ['time-tz-select', 't2d-tz-select', 'd2t-tz-select'];
    const systemTz = -new Date().getTimezoneOffset() / 60;
    selects.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        for (let i = -12; i <= 14; i++) {
            const opt = document.createElement('option');
            opt.value = i;
            opt.textContent = 'UTC' + (i >= 0 ? '+' : '') + i;
            if (i === systemTz) opt.selected = true;
            select.appendChild(opt);
        }
    });
}

async function updateClock() {
    const offset = parseInt(document.getElementById('time-tz-select').value);
    const res = await pywebview.api.get_current_time(offset);
    if (res.success) {
        document.getElementById('time-now-ts').value = res.data.ts;
        document.getElementById('time-now-date').value = res.data.date;
    }
}

async function tsToDate() {
    const ts = document.getElementById('ts-input').value;
    const offset = parseInt(document.getElementById('t2d-tz-select').value);
    const isIos = document.getElementById('t2d-ios').checked;
    const res = await pywebview.api.ts_to_date(ts, offset, isIos);
    if (res.success) {
        document.getElementById('date-output').value = res.data;
    } else {
        showAlert(res.error);
    }
}

async function dateToTs() {
    const date = document.getElementById('date-input').value;
    const offset = parseInt(document.getElementById('d2t-tz-select').value);
    const isIos = document.getElementById('d2t-ios').checked;
    const res = await pywebview.api.date_to_ts(date, offset, isIos);
    if (res.success) {
        document.getElementById('ts-output').value = res.data;
    } else {
        showAlert(res.error);
    }
}

let cpState = {
    img: null,
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    isDragging: false,
    lastMouseX: 0,
    lastMouseY: 0,
    baseScale: 1
};

// Color Picker logic
async function selectColorPickerFile() {
    const res = await pywebview.api.select_file(['Image files (*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.ico;*.heic;*.heif;*.tiff;*.tif;*.gif)', 'All files (*.*)']);
    if (res.success && res.data) {
        document.getElementById('img-color-src').value = res.data;
        const fileRes = await pywebview.api.image_to_base64_data(res.data);
        if (fileRes.success) {
            cpState.img = new Image();
            cpState.img.onload = function() {
                document.getElementById('color-picker-main').style.display = 'block';
                document.getElementById('color-result-container').style.display = 'block';
                resetColorPicker();
            };
            cpState.img.src = fileRes.data;
        } else {
            showAlert(fileRes.error);
        }
    }
}

function resetColorPicker() {
    if (!cpState.img) return;
    const container = document.getElementById('color-canvas-container');
    const cw = container.clientWidth;
    const ch = container.clientHeight;
    
    cpState.baseScale = Math.min(cw / cpState.img.width, ch / cpState.img.height);
    cpState.scale = cpState.baseScale;
    cpState.offsetX = (cw - cpState.img.width * cpState.scale) / 2;
    cpState.offsetY = (ch - cpState.img.height * cpState.scale) / 2;
    
    drawCPCanvas();
}

function zoomColorPicker(factor) {
    if (!cpState.img) return;
    cpState.scale *= factor;
    drawCPCanvas();
}

function drawCPCanvas() {
    const canvas = document.getElementById('color-canvas');
    const container = document.getElementById('color-canvas-container');
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    
    // Only resize if container size changed to avoid clearing and "jumping"
    if (canvas.width !== container.clientWidth || canvas.height !== container.clientHeight) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
    }
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (cpState.img) {
        ctx.drawImage(cpState.img, cpState.offsetX, cpState.offsetY, cpState.img.width * cpState.scale, cpState.img.height * cpState.scale);
    }
}

function initColorPicker() {
    const container = document.getElementById('color-canvas-container');
    const canvas = document.getElementById('color-canvas');
    if (!container || !canvas) return;

    container.addEventListener('mousedown', (e) => {
        if (!cpState.img) return;
        // Only track if it's the primary mouse button
        if (e.button !== 0) return;
        
        cpState.isDragging = false;
        cpState.dragStarted = false;
        cpState.lastMouseX = e.clientX;
        cpState.lastMouseY = e.clientY;
        
        // Prevent default to avoid image ghosting/selection which causes jumps
        e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
        if (e.buttons === 1 && cpState.img) {
            const currentX = e.clientX;
            const currentY = e.clientY;
            
            if (!cpState.isDragging) {
                const dx = Math.abs(currentX - cpState.lastMouseX);
                const dy = Math.abs(currentY - cpState.lastMouseY);
                if (dx > 2 || dy > 2) {
                    cpState.isDragging = true;
                    cpState.dragStarted = true;
                    container.style.cursor = 'grabbing';
                    // Synchronize last position when starting drag to avoid initial jump
                    cpState.lastMouseX = currentX;
                    cpState.lastMouseY = currentY;
                }
            } else {
                const movX = currentX - cpState.lastMouseX;
                const movY = currentY - cpState.lastMouseY;
                cpState.offsetX += movX;
                cpState.offsetY += movY;
                cpState.lastMouseX = currentX;
                cpState.lastMouseY = currentY;
                drawCPCanvas();
            }
        }
    });

    window.addEventListener('mouseup', () => {
        cpState.isDragging = false;
        if (container) container.style.cursor = 'grab';
    });

    canvas.addEventListener('click', (e) => {
        if (cpState.dragStarted) {
            cpState.dragStarted = false;
            return;
        }
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const pixel = ctx.getImageData(x, y, 1, 1).data;
        
        

        const r = pixel[0], g = pixel[1], b = pixel[2], aRaw = pixel[3]; const a = (aRaw / 255).toFixed(2);
        const toHex = (n) => n.toString(16).padStart(2, "0").toUpperCase(); const hexRGBA = "#" + toHex(r) + toHex(g) + toHex(b) + toHex(aRaw); const hexARGB = "#" + toHex(aRaw) + toHex(r) + toHex(g) + toHex(b); const [h, s, l] = rgbToHsl(r, g, b); const hsla = "hsla(" + h + ", " + s + "%, " + l + "%, " + a + ")";
        const rgba = `rgba(${r}, ${g}, ${b}, ${a})`;
        
        document.getElementById('color-hex-rgba').value = hexRGBA; document.getElementById('color-hex-argb').value = hexARGB; document.getElementById('color-hsla').value = hsla;
        document.getElementById('color-rgba').value = rgba;
        document.getElementById('color-preview').style.backgroundColor = rgba;
    });
}

// Image Tools
async function imgConvert() {
    const src = document.getElementById('img-conv-src').value;
    const fmt = document.getElementById('img-conv-fmt').value;
    if (!src) { showAlert('请先选择图片'); return; }
    
    const ext = src.split('.').pop().toLowerCase();
    const targetFmt = fmt.toLowerCase();
    const isSame = (ext === targetFmt) || (ext === 'jpg' && targetFmt === 'jpeg') || (ext === 'jpeg' && targetFmt === 'jpg');
    
    if (isSame) {
        showToast('原格式与目标格式相同，无需转换');
        return;
    }

    const saveExt = targetFmt === 'jpeg' ? 'jpg' : targetFmt;
    const saveRes = await pywebview.api.save_file_api('converted.' + saveExt, [['Image', '*.' + saveExt]]);
    if (!saveRes.success) return;
    const savePath = saveRes.data;

    const btn = document.getElementById('btn-img-conv');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '转换中...';

    try {
        const res = await pywebview.api.image_convert(src, fmt, savePath);
        if (res.success) showToast('转换成功');
        else if (res.error !== 'Cancelled or failed') showAlert(res.error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function imgCompress() {
    const src = document.getElementById('img-comp-src').value;
    const quality = parseInt(document.getElementById('img-comp-quality').value);
    if (!src) { showAlert('请先选择图片'); return; }

    const extOrig = src.split('.').pop().toLowerCase();
    const ext = (extOrig === 'jpg' || extOrig === 'jpeg') ? 'jpg' : extOrig;
    const saveRes = await pywebview.api.save_file_api('compressed.' + ext, [['Image', '*.' + ext]]);
    if (!saveRes.success) return;
    const savePath = saveRes.data;

    const btn = document.getElementById('btn-img-comp');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '保存中...';

    try {
        const res = await pywebview.api.image_compress(src, quality, savePath);
        if (res.success) showToast('压缩成功');
        else if (res.error !== 'Cancelled or failed') showAlert(res.error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}


document.getElementById('img-comp-quality')?.addEventListener('input', (e) => {
    document.getElementById('quality-val').textContent = e.target.value;
});

function onWidthChange() {
    if (window.__resetting) return;
    const ratioCheck = document.getElementById('img-ratio');
    if (!ratioCheck || !ratioCheck.checked || currentAspectRatio === 0) return;
    const widthInput = document.getElementById('img-width');
    const heightInput = document.getElementById('img-height');
    let w = parseFloat(widthInput.value);
    if (isNaN(w) || w <= 0) return;
    let newHeight = w / currentAspectRatio;
    if (!isNaN(newHeight) && isFinite(newHeight)) {
        window.__resetting = true;
        heightInput.value = Math.round(newHeight);
        window.__resetting = false;
    }
}

function onHeightChange() {
    if (window.__resetting) return;
    const ratioCheck = document.getElementById('img-ratio');
    if (!ratioCheck || !ratioCheck.checked || currentAspectRatio === 0) return;
    const widthInput = document.getElementById('img-width');
    const heightInput = document.getElementById('img-height');
    let h = parseFloat(heightInput.value);
    if (isNaN(h) || h <= 0) return;
    let newWidth = h * currentAspectRatio;
    if (!isNaN(newWidth) && isFinite(newWidth)) {
        window.__resetting = true;
        widthInput.value = Math.round(newWidth);
        window.__resetting = false;
    }
}

document.getElementById('img-width')?.addEventListener('input', onWidthChange);
document.getElementById('img-height')?.addEventListener('input', onHeightChange);

const imaRatioCheck = document.getElementById('img-ratio');
if (imaRatioCheck) {
    imaRatioCheck.addEventListener('change', async (e) => {
        if (!imaRatioCheck.checked) return;
        const src = document.getElementById('img-size-src').value;
        if (!src) return;
        const infoRes = await pywebview.api.get_image_info(src);
        if (infoRes.success) {
            window.__resetting = true;
            document.getElementById('img-width').value = infoRes.data.width;
            document.getElementById('img-height').value = infoRes.data.height;
            currentAspectRatio = infoRes.data.width / infoRes.data.height;
            window.__resetting = false;
        }
    });
}

async function imgSize() {
    const src = document.getElementById('img-size-src').value;
    const w = parseInt(document.getElementById('img-width').value);
    const h = parseInt(document.getElementById('img-height').value);
    const mode = document.getElementById('img-size-mode').value;
    if (!src) { showAlert('请先选择图片'); return; }
    if (isNaN(w) || isNaN(h)) { showAlert('请输入正确的尺寸'); return; }
    if (w <= 0 || h <= 0) { showAlert('目标尺寸 must be > 0'); return; }

    const ext = src.split('.').pop().toLowerCase();
    const saveRes = await pywebview.api.save_file_api('processed.' + ext, [['Image', '*.' + ext]]);
    if (!saveRes.success) return;
    const savePath = saveRes.data;

    const btn = document.getElementById('btn-img-size');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '保存中...';

    try {
        const res = await pywebview.api.image_resize_crop(src, w, h, mode, savePath);
        if (res.success) showToast('调整成功');
        else if (res.error !== 'Cancelled or failed') showAlert(res.error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function imgRadius() {
    const src = document.getElementById('img-radius-src').value;
    if (!src) { showAlert('请先选择图片'); return; }
    let radii;
    if (document.getElementById('rad-mode-unified').checked) {
        const val = parseInt(document.getElementById('rad-all').value) || 0;
        radii = [val, val, val, val];
    } else {
        radii = ['rad-tl', 'rad-tr', 'rad-bl', 'rad-br'].map(id => parseInt(document.getElementById(id).value) || 0);
    }
    if (radii.some(r => r < 0)) {
        showAlert('圆角值不能为负数');
        return;
    }

    const saveRes = await pywebview.api.save_file_api('rounded.png', [['PNG', '*.png']]);
    if (!saveRes.success) return;
    const savePath = saveRes.data;

    const btn = document.getElementById('btn-img-radius');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '保存中...';

    try {
        const res = await pywebview.api.image_radius(src, radii, savePath);
        if (res.success) showToast('圆角处理成功');
        else if (res.error !== 'Cancelled or failed') showAlert(res.error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function imgToBase64() {
    const src = document.getElementById('img2b64-src').value;
    if (!src) { showAlert('请先选择图片'); return; }
    const res = await pywebview.api.image_to_base64_save(src);
    if (res.success) showToast('转换并保存成功');
    else if (res.error !== 'Cancelled or failed') showAlert(res.error);
}

async function base64ToImg() {
    const data = document.getElementById('b64-input').value;
    if (!data) { showAlert('请输入Base64字符串'); return; }
    
    const btn = document.getElementById('btn-b64-to-img');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '还原中...';

    try {
        const res = await pywebview.api.base64_to_image(data);
        if (res.success) showToast('还原成功');
        else if (res.error !== 'Cancelled or failed') showAlert(res.error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Generate Tools
async function generateQR() {
    const data = document.getElementById('qr-input').value;
    if (!data) return;
    const res = await pywebview.api.generate_qr(data);
    if (res.success) {
        const container = document.getElementById('qr-result');
        container.innerHTML = '<img id="generated-qr-img" src="' + res.data + '" alt="QR Code">';
        document.getElementById('qr-result-container').style.display = 'flex';
        document.getElementById('qr-empty-hint').style.display = 'none';
    } else {
        showAlert(res.error);
    }
}

async function saveQR() {
    const img = document.getElementById('generated-qr-img');
    if (!img) return;
    const res = await pywebview.api.save_image_from_base64(img.src, "qrcode.png");
    if (res.success) showToast('保存成功');
    else if (res.error !== 'Cancelled or failed') showAlert(res.error);
}

async function decodeQR() {
    const src = document.getElementById('qr-rec-src').value;
    if (!src) { showAlert('请先选择图片'); return; }
    const res = await pywebview.api.decode_qr(src);
    if (res.success) {
        document.getElementById('qr-rec-output').value = res.data;
        showToast('识别成功');
    } else {
        showAlert(res.error);
    }
}

async function generateUUIDs() {
    const count = parseInt(document.getElementById('uuid-count').value);
    const hyphen = document.getElementById('uuid-hyphen').checked;
    const upper = document.getElementById('uuid-upper').checked;
    const braces = document.getElementById('uuid-braces').checked;
    const res = await pywebview.api.generate_uuids(count, hyphen, upper, braces);
    if (res.success) {
        document.getElementById('uuid-output').value = res.data;
    } else {
        showAlert(res.error);
    }
}

function initUUIDListeners() {
    ['uuid-hyphen', 'uuid-upper', 'uuid-braces'].forEach(id => {
        document.getElementById(id).addEventListener('change', async () => {
            const hyphen = document.getElementById('uuid-hyphen').checked;
            const upper = document.getElementById('uuid-upper').checked;
            const braces = document.getElementById('uuid-braces').checked;
            const res = await pywebview.api.format_uuids_api(hyphen, upper, braces);
            if (res.success && res.data) {
                document.getElementById('uuid-output').value = res.data;
            }
        });
    });
}

// Query Tools
function initAsciiTable() {
    const tbody = document.querySelector('#ascii-table tbody');
    if (!tbody) return;
    const controlChars = [
        ["0000 0000", "000", "0", "0x00", "NUL", "Null (空字符)"],
        ["0000 0001", "001", "1", "0x01", "SOH", "Start of Heading (标题开始)"],
        ["0000 0010", "002", "2", "0x02", "STX", "Start of Text (正文开始)"],
        ["0000 0011", "003", "3", "0x03", "ETX", "End of Text (正文结束)"],
        ["0000 0100", "004", "4", "0x04", "EOT", "End of Transmission (传输结束)"],
        ["0000 0101", "005", "5", "0x05", "ENQ", "Enquiry (询问)"],
        ["0000 0110", "006", "6", "0x06", "ACK", "Acknowledgment (确认)"],
        ["0000 0111", "007", "7", "0x07", "BEL", "Bell (响铃)"],
        ["0000 1000", "010", "8", "0x08", "BS", "Backspace (退格)"],
        ["0000 1001", "011", "9", "0x09", "HT", "Horizontal Tab (水平制表符)"],
        ["0000 1010", "012", "10", "0x0A", "LF", "Line Feed (换换)"],
        ["0000 1011", "013", "11", "0x0B", "VT", "Vertical Tab (垂直制表符)"],
        ["0000 1100", "014", "12", "0x0C", "FF", "Form Feed (换页)"],
        ["0000 1101", "015", "13", "0x0D", "CR", "Carriage Return (回车)"],
        ["0000 1110", "016", "14", "0x0E", "SO", "Shift Out (不用切换)"],
        ["0000 1111", "017", "15", "0x0F", "SI", "Shift In (启用切换)"],
        ["0001 0000", "020", "16", "0x10", "DLE", "Data Link Escape (数据链路转义)"],
        ["0001 0001", "021", "17", "0x11", "DC1", "Device Control 1 (设备控制1)"],
        ["0001 0010", "022", "18", "0x12", "DC2", "Device Control 2 (设备控制2)"],
        ["0001 0011", "023", "19", "0x13", "DC3", "Device Control 3 (设备控制3)"],
        ["0001 0100", "024", "20", "0x14", "DC4", "Device Control 4 (设备控制4)"],
        ["0001 0101", "025", "21", "0x15", "NAK", "Negative Acknowledgment (否定确认)"],
        ["0001 0110", "026", "22", "0x16", "SYN", "Synchronous Idle (同步空闲)"],
        ["0001 0111", "027", "23", "0x17", "ETB", "End of Transmission Block (传输块结束)"],
        ["0001 1000", "030", "24", "0x18", "CAN", "Cancel (取消)"],
        ["0001 1001", "031", "25", "0x19", "EM", "End of Medium (介质结束)"],
        ["0001 1010", "032", "26", "0x1A", "SUB", "Substitute (替换)"],
        ["0001 1011", "033", "27", "0x1B", "ESC", "Escape (转义)"],
        ["0001 1100", "034", "28", "0x1C", "FS", "File Separator (文件分隔符)"],
        ["0001 1101", "035", "29", "0x1D", "GS", "Group Separator (组分隔符)"],
        ["0001 1110", "036", "30", "0x1E", "RS", "Record Separator (记录分隔符)"],
        ["0001 1111", "037", "31", "0x1F", "US", "Unit Separator (单元分隔符)"],
        ["0010 0000", "040", "32", "0x20", "Space", "Space (空格)"],
    ];
    controlChars.forEach(row => {
        const tr = document.createElement('tr');
        row.forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    for (let i = 33; i < 127; i++) {
        const tr = document.createElement('tr');
        const bin = i.toString(2).padStart(8, '0');
        const data = [bin.slice(0, 4) + ' ' + bin.slice(4), i.toString(8).padStart(3, '0'), i.toString(10), '0x' + i.toString(16).toUpperCase().padStart(2, '0'), String.fromCharCode(i), ''];
        data.forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    }
    const delTr = document.createElement('tr');
    ["0111 1111", "177", "127", "0x7F", "DEL", "Delete (删除)"].forEach(cell => {
        const td = document.createElement('td');
        td.textContent = cell;
        delTr.appendChild(td);
    });
    tbody.appendChild(delTr);
}

// Init on Load
window.addEventListener('pywebviewready', () => {
    initTimeZones();
    updateClock();
    initAsciiTable();
    initUUIDListeners();
    initBaseConvListeners();
    initColorPicker();
    initContextMenu();
    initPermissionSearch();
    initCustomTooltip();
    initQRCharCount();
    // AI 聊天仅 macOS 可用
    if (!navigator.platform.toLowerCase().includes('mac')) {
        const aichatBtn = document.querySelector('[data-tab="aichat"]');
        if (aichatBtn) aichatBtn.style.display = 'none';
    }

    addApiHeaderRow("User-Agent", "Mozilla/5.0 (DeveloperTools)");
    loadLocalPermissions();

    // 加密解密：文件/文本模式切换时联动显示/隐藏格式行和结果卡
    document.querySelectorAll('.sub-nav-item[data-sub="crypto-text"], .sub-nav-item[data-sub="crypto-file"]').forEach(btn => {
        btn.addEventListener('click', () => setTimeout(updateCryptoFileModeUI, 0));
    });
    updateCryptoFileModeUI();

    // AI 聊天子标签切换
    document.querySelectorAll('#aichat-tabs .sub-nav-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();  // 防止触发外层 .sub-nav-item 的通用处理
            document.querySelectorAll('#aichat-tabs .sub-nav-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const url = btn.dataset.url;
            const tabId = btn.textContent.trim();
            pywebview.api.embed_browser_show_tab(tabId, url);
        });
    });

    // 加密解密：算法子标签切换时更新 UI
    document.querySelectorAll('.sub-nav-item[data-sub^="crypto-algo-"]').forEach(btn => {
        btn.addEventListener('click', () => setTimeout(updateCryptoAlgoTabUI, 0));
    });
    // 初始加载时设置默认标签（AES）的密钥/IV 占位提示
    setTimeout(onCryptoCfgChange, 0);

    // Special handler for API Main Tabs (Request/Response)
    document.querySelectorAll('.sub-nav-item[data-sub^="api-"]').forEach(btn => {
        if (btn.id === 'api-req-nav-btn' || btn.id === 'api-res-nav-btn') {
            btn.addEventListener('click', (e) => {
                e.stopImmediatePropagation();
                const parent = btn.closest('.card');

                // 1. Switch Main Tabs
                parent.querySelectorAll('.api-main-tab-content').forEach(c => c.classList.remove('active'));
                parent.querySelectorAll('#api-req-nav-btn, #api-res-nav-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const targetPanel = document.getElementById(btn.dataset.sub);
                targetPanel.classList.add('active');

                // 2. Ensure internal sub-tabs have an active state so content isn't blank
                const activeSub = targetPanel.querySelector('.sub-tab-content.active');
                if (!activeSub) {
                    // If nothing is active (like when first switching back), activate the first sub-nav item
                    const firstSubBtn = targetPanel.querySelector('.sub-nav-item');
                    if (firstSubBtn) firstSubBtn.click();
                }
            });
        }
    });

});

// Context Menu Logic
function initContextMenu() {
    const menu = document.getElementById('context-menu');
    const tables = ['http-status-table', 'android-perm-table', 'port-table'];
    let selectedRow = null;
    let selectedTableId = null;

    if (!menu) return;

    // 禁用全局右键菜单，防止显示 Reload / Inspect Element
    document.addEventListener('contextmenu', e => e.preventDefault());

    tables.forEach(id => {
        const table = document.getElementById(id);
        if (!table) return;
        table.addEventListener('contextmenu', (e) => {
            const row = e.target.closest('tr');
            if (row && row.parentElement.tagName === 'TBODY') {
                e.preventDefault();
                selectedRow = row;
                selectedTableId = id;
                
                const copyNameItem = document.getElementById('menu-copy');
                const copyDescItem = document.getElementById('menu-copy-code');
                const copyAllItem = document.getElementById('menu-copy-all');
                
                if (id === 'http-status-table' || id === 'port-table') {
                    copyNameItem.textContent = '复制';
                    copyDescItem.style.display = 'none';
                    copyAllItem.style.display = 'none';
                } else if (id === 'android-perm-table') {
                    copyNameItem.textContent = '复制名字';
                    copyDescItem.textContent = '复制描述';
                    copyDescItem.style.display = 'block';
                    copyAllItem.style.display = 'block';
                }
                
                menu.style.display = 'block';
                menu.style.left = e.clientX + 'px';
                menu.style.top = e.clientY + 'px';
            }
        });
    });

    document.addEventListener('mousedown', (e) => {
        if (!menu.contains(e.target)) {
            menu.style.display = 'none';
        }
    });

    window.addEventListener('blur', () => {
        menu.style.display = 'none';
    });

    document.getElementById('menu-copy').addEventListener('click', () => {
        if (selectedRow) {
            let text;
            if (selectedTableId === 'android-perm-table') {
                text = selectedRow.cells[0].textContent;
                showToast('已复制名字');
            } else {
                text = Array.from(selectedRow.cells).map(cell => cell.textContent.trim()).join(' ');
                showToast('已复制整行内容');
            }
            navigator.clipboard.writeText(text);
            menu.style.display = 'none';
        }
    });

    document.getElementById('menu-copy-code').addEventListener('click', () => {
        if (selectedRow) {
            const text = selectedRow.cells[selectedRow.cells.length - 1].textContent;
            navigator.clipboard.writeText(text);
            showToast('已复制描述');
            menu.style.display = 'none';
        }
    });

    document.getElementById('menu-copy-all').addEventListener('click', () => {
        if (selectedRow) {
            const text = Array.from(selectedRow.cells).map(cell => cell.textContent.trim()).join(' ');
            navigator.clipboard.writeText(text);
            showToast('已复制整行内容');
            menu.style.display = 'none';
        }
    });
}

function initCustomTooltip() {
    const tooltip = document.getElementById('custom-tooltip');
    if (!tooltip) return;

    document.addEventListener('mouseover', (e) => {
        const target = e.target.closest('[data-tooltip]');
        if (target) {
            const text = target.dataset.tooltip;
            if (!text || text === '-') return;
            
            tooltip.textContent = text;
            tooltip.style.display = 'block';
            
            const rect = target.getBoundingClientRect();
            const tooltipHeight = tooltip.offsetHeight;
            const tooltipWidth = tooltip.offsetWidth;
            
            // Position above the element
            let top = rect.top - tooltipHeight - 8;
            let left = rect.left;
            
            // Boundary checks
            if (top < 10) {
                top = rect.bottom + 8; // Show below if no space above
            }
            if (left + tooltipWidth > window.innerWidth - 10) {
                left = window.innerWidth - tooltipWidth - 10;
            }
            if (left < 10) left = 10;
            
            tooltip.style.top = top + 'px';
            tooltip.style.left = left + 'px';
        }
    });

    document.addEventListener('mouseout', (e) => {
        if (e.target.closest('[data-tooltip]')) {
            tooltip.style.display = 'none';
        }
    });
}

function initQRCharCount() {
    const input = document.getElementById('qr-input');
    const display = document.getElementById('qr-char-count');
    if (input && display) {
        input.addEventListener('input', () => {
            display.textContent = input.value.length;
        });
    }
}

function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;
    if (max === min) { h = s = 0; }
    else {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
    }
    return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
}

// API Test Logic
function addApiHeaderRow(key = '', value = '') {
    const list = document.getElementById('api-header-list');
    const row = document.createElement('div');
    row.className = 'input-row';
    row.style.marginBottom = '0px';
    row.innerHTML = `
        <input type="text" placeholder="Key" class="api-header-key" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" value="${key}" style="flex: 2;">
        <input type="text" placeholder="Value" class="api-header-val" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" value="${value}" style="flex: 4;">
        <button class="small-btn" onclick="this.parentElement.remove()" title="删除"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
    `;
    list.appendChild(row);
}



let lastRawResponse = '';

function showRawResponse() {
    document.getElementById('api-res-body').value = lastRawResponse;
}

function generateRandomUserAgent() {
        const uas = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/119.0 Firefox/119.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) CriOS/120.0.6099.101 Mobile/15E148 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.115 Safari/537.36 OPR/88.0.4412.74',
        'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko'
    ];
    const randomUA = uas[Math.floor(Math.random() * uas.length)];
    
    let found = false;
    document.querySelectorAll("#api-header-list .input-row").forEach(row => {
        const keyEl = row.querySelector(".api-header-key");
        const valEl = row.querySelector(".api-header-val");
        if (keyEl && keyEl.value.trim().toLowerCase() === "user-agent") {
            valEl.value = randomUA;
            found = true;
        }
    });
    
    if (!found) {
        addApiHeaderRow("User-Agent", randomUA);
    }
}

async function sendApiRequest() {
    const url = document.getElementById('api-url').value.trim();
    const method = document.getElementById('api-method').value;
    const body = document.getElementById('api-body-content').value;
    const btn = document.getElementById('api-send-btn');
    const defaultContentType = document.getElementById('api-content-type').value;

    if (!url) { showAlert('请输入请求 URL'); return; }
    if (!url.startsWith('http')) { showAlert('URL 必须以 http:// 或 https:// 开头'); return; }

    const headers = {};
    let hasContentType = false;
    document.querySelectorAll('#api-header-list .input-row').forEach(row => {
        const keyEl = row.querySelector('.api-header-key');
        const valEl = row.querySelector('.api-header-val');
        if (keyEl && valEl) {
            const key = keyEl.value.trim();
            const val = valEl.value.trim();
            if (key) {
                headers[key] = val;
                if (key.toLowerCase() === 'content-type') hasContentType = true;
            }
        }
    });

    if (!hasContentType && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        headers['Content-Type'] = defaultContentType;
    }

    btn.disabled = true;
    btn.textContent = '发送中...';
    
    try {
        const ignoreSSL = document.getElementById('api-ignore-ssl').checked;
        const res = await pywebview.api.request_api(url, method, JSON.stringify(headers), body, ignoreSSL);
        
        // Show Response Tab
        document.getElementById('api-res-nav-btn').click();
        
        const statusEl = document.getElementById('api-res-status');
        const bodyEl = document.getElementById('api-res-body');
        const headEl = document.getElementById('api-res-headers');
        const resContainer = document.getElementById('api-response-container');
        const errContainer = document.getElementById('api-error-container');
        const emptyHint = document.getElementById('api-empty-res-hint');
        const errMsgEl = document.getElementById('api-error-message');

        emptyHint.style.display = 'none';

        if (res.success) {
            resContainer.style.display = 'flex';
            errContainer.style.display = 'none';

            const data = res.data;
            statusEl.textContent = data.status;
            
            if (data.status >= 200 && data.status < 300) {
                statusEl.style.backgroundColor = '#4CD964';
                statusEl.style.color = '#fff';
            } else {
                statusEl.style.backgroundColor = '#FF3B30';
                statusEl.style.color = '#fff';
            }

            lastRawResponse = data.body;
            bodyEl.value = data.body;
            refreshRender();

            let headText = '';
            for (const [k, v] of Object.entries(data.headers)) {
                headText += k + ': ' + v + '\n';
            }
            headEl.value = headText;

            // Populate Request Headers from backend data
            const reqHeadEl = document.getElementById('api-res-req-headers');
            let reqHeadText = '';
            const actualReqHeaders = data.request_headers || headers;
            for (const [k, v] of Object.entries(actualReqHeaders)) {
                reqHeadText += k + ': ' + v + '\n';
            }
            reqHeadEl.value = reqHeadText;
        } else {
            // Network error (status -1)
            resContainer.style.display = 'none';
            errContainer.style.display = 'flex';
            errMsgEl.value = res.error;
            
            statusEl.textContent = '-1';
        }
    } catch (e) {
        // App logic error
        document.getElementById('api-res-nav-btn').click();
        document.getElementById('api-response-container').style.display = 'none';
        document.getElementById('api-error-container').style.display = 'flex';
        document.getElementById('api-error-message').value = '异常: ' + e;
    } finally {
        btn.disabled = false;
        btn.textContent = '发送请求';
    }
}

async function formatApiResponse(type) {
    const el = document.getElementById('api-res-body');
    const val = el.value.trim();
    if (!val) return;
    
    try {
        if (type === 'json') {
            const obj = JSON.parse(val);
            el.value = JSON.stringify(obj, null, 4);
        } else if (type === 'html') {
            // Re-use backend formatting for HTML/XML
            const res = await pywebview.api.format_data(val, 'html_format');
            if (res.success) {
                el.value = res.data;
            } else {
                showToast('HTML 格式化失败: ' + res.error);
            }
        }
    } catch (e) {
        showToast('格式化异常: ' + e.message);
    }
}

function refreshRender() {
    const html = document.getElementById('api-res-body').value;
    const frame = document.getElementById('api-res-render-frame');
    if (frame) {
        frame.srcdoc = html;
    }
}
