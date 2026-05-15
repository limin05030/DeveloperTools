// Tab Switching Logic
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
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
async function selectFile(id) {
    const res = await pywebview.api.select_file();
    if (res.success && res.data) {
        document.getElementById(id).value = res.data;
        if (id === 'img-size-src') {
            const infoRes = await pywebview.api.get_image_info(res.data);
            if (infoRes.success) {
                document.getElementById('img-width').value = infoRes.data.width;
                document.getElementById('img-height').value = infoRes.data.height;
            }
        }
    } else if (!res.success && res.error !== 'Cancelled') {
        showAlert(res.error);
    }
}

async function loadBase64File() {
    const res = await pywebview.api.read_text_file();
    if (res.success) {
        document.getElementById('b64-input').value = res.data;
    } else if (!res.success && res.error !== 'Cancelled') {
        showAlert(res.error);
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

// Format Tools
async function formatData(type) {
    const isFileMode = document.querySelector('[data-sub="format-file"]').classList.contains('active');
    if (isFileMode) {
        showAlert('文件模式格式化暂未实现，请使用文本模式');
        return;
    }
    const data = document.getElementById('format-input').value;
    if (!data) return;
    const res = await pywebview.api.format_data(data, type);
    if (res.success) {
        document.getElementById('format-output').value = res.data;
    } else {
        showAlert(res.error);
    }
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

    const res = await pywebview.api.image_convert(src, fmt);
    if (res.success) showToast('转换成功');
    else if (res.error !== 'Cancelled or failed') showAlert(res.error);
}

async function imgCompress() {
    const src = document.getElementById('img-comp-src').value;
    const quality = parseInt(document.getElementById('img-comp-quality').value);
    if (!src) { showAlert('请先选择图片'); return; }
    const res = await pywebview.api.image_compress(src, quality);
    if (res.success) showToast('压缩成功');
    else if (res.error !== 'Cancelled or failed') showAlert(res.error);
}

document.getElementById('img-comp-quality')?.addEventListener('input', (e) => {
    document.getElementById('quality-val').textContent = e.target.value;
});

async function imgSize() {
    const src = document.getElementById('img-size-src').value;
    const w = parseInt(document.getElementById('img-width').value);
    const h = parseInt(document.getElementById('img-height').value);
    const mode = document.getElementById('img-size-mode').value;
    if (!src) { showAlert('请先选择图片'); return; }
    if (isNaN(w) || isNaN(h)) { showAlert('请输入正确的尺寸'); return; }
    const res = await pywebview.api.image_resize_crop(src, w, h, mode);
    if (res.success) showToast('调整成功');
    else if (res.error !== 'Cancelled or failed') showAlert(res.error);
}

function toggleRadiusMode() {
    const isUnified = document.getElementById('rad-mode-unified').checked;
    document.getElementById('rad-all').disabled = !isUnified;
    document.getElementById('rad-tl').disabled = isUnified;
    document.getElementById('rad-tr').disabled = isUnified;
    document.getElementById('rad-bl').disabled = isUnified;
    document.getElementById('rad-br').disabled = isUnified;
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
    const res = await pywebview.api.image_radius(src, radii);
    if (res.success) showToast('圆角处理成功');
    else if (res.error !== 'Cancelled or failed') showAlert(res.error);
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
    const res = await pywebview.api.base64_to_image(data);
    if (res.success) showToast('还原成功');
    else if (res.error !== 'Cancelled or failed') showAlert(res.error);
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
});
