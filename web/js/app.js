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

// Helper Functions
async function selectFile(id) {
    const result = await pywebview.api.select_file();
    let path = Array.isArray(result) ? result[0] : result;
    if (path && typeof path === 'string' && !path.startsWith('Error:')) {
        document.getElementById(id).value = path;
        if (id === 'img-size-src') {
            const info = await pywebview.api.get_image_info(path);
            if (info && !info.error) {
                document.getElementById('img-width').value = info.width;
                document.getElementById('img-height').value = info.height;
            }
        }
    } else if (path && path.startsWith('Error:')) {
        alert(path);
    }
}

async function loadBase64File() {
    const content = await pywebview.api.read_text_file();
    if (content && !content.startsWith('Error:')) {
        document.getElementById('b64-input').value = content;
    } else if (content && content.startsWith('Error:')) {
        alert(content);
    }
}

async function copyToClipboard(id) {
    const val = document.getElementById(id).value;
    if (val) {
        navigator.clipboard.writeText(val);
    }
}

async function copyValue(id) {
    const val = document.getElementById(id).value;
    if (val) {
        navigator.clipboard.writeText(val);
    }
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
    let result;
    if (isFileMode) {
        const path = document.getElementById('hash-file-path').value;
        if (!path) { alert('请先选择文件'); return; }
        result = await pywebview.api.calc_file_hash(path, algo, isHmac, key);
    } else {
        const data = document.getElementById('hash-input').value;
        if (!data) return;
        result = await pywebview.api.calc_hash(data, algo, isHmac, key);
    }
    document.getElementById('hash-output').value = result;
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
    const result = await pywebview.api.encode_decode(data, action);
    document.getElementById('encode-output').value = result;
}

// Format Tools
async function formatData(type) {
    const isFileMode = document.querySelector('[data-sub="format-file"]').classList.contains('active');
    let data;
    if (isFileMode) {
        alert('文件模式格式化暂未实现，请使用文本模式');
        return;
    } else {
        data = document.getElementById('format-input').value;
    }
    if (!data) return;
    const result = await pywebview.api.format_data(data, type);
    document.getElementById('format-output').value = result;
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
    const result = await pywebview.api.get_current_time(offset);
    document.getElementById('time-now-ts').value = result.ts;
    document.getElementById('time-now-date').value = result.date;
}

async function tsToDate() {
    const ts = document.getElementById('ts-input').value;
    const offset = parseInt(document.getElementById('t2d-tz-select').value);
    const isIos = document.getElementById('t2d-ios').checked;
    const result = await pywebview.api.ts_to_date(ts, offset, isIos);
    document.getElementById('date-output').value = result;
}

async function dateToTs() {
    const date = document.getElementById('date-input').value;
    const offset = parseInt(document.getElementById('d2t-tz-select').value);
    const isIos = document.getElementById('d2t-ios').checked;
    const result = await pywebview.api.date_to_ts(date, offset, isIos);
    document.getElementById('ts-output').value = result;
}

// Image Tools
async function imgConvert() {
    const src = document.getElementById('img-conv-src').value;
    const fmt = document.getElementById('img-conv-fmt').value;
    if (!src) { alert('请先选择图片'); return; }
    const res = await pywebview.api.image_convert(src, fmt);
    if (res && res.startsWith('Error')) alert(res);
}

async function imgCompress() {
    const src = document.getElementById('img-comp-src').value;
    const quality = parseInt(document.getElementById('img-comp-quality').value);
    if (!src) { alert('请先选择图片'); return; }
    const res = await pywebview.api.image_compress(src, quality);
    if (res && res.startsWith('Error')) alert(res);
}

document.getElementById('img-comp-quality')?.addEventListener('input', (e) => {
    document.getElementById('quality-val').textContent = e.target.value;
});

async function imgSize() {
    const src = document.getElementById('img-size-src').value;
    const w = parseInt(document.getElementById('img-width').value);
    const h = parseInt(document.getElementById('img-height').value);
    const mode = document.getElementById('img-size-mode').value;
    if (!src) { alert('请先选择图片'); return; }
    if (isNaN(w) || isNaN(h)) { alert('请输入正确的尺寸'); return; }
    const res = await pywebview.api.image_resize_crop(src, w, h, mode);
    if (res && res.startsWith('Error')) alert(res);
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
    if (!src) { alert('请先选择图片'); return; }
    let radii;
    if (document.getElementById('rad-mode-unified').checked) {
        const val = parseInt(document.getElementById('rad-all').value) || 0;
        radii = [val, val, val, val];
    } else {
        radii = ['rad-tl', 'rad-tr', 'rad-bl', 'rad-br'].map(id => parseInt(document.getElementById(id).value) || 0);
    }
    const res = await pywebview.api.image_radius(src, radii);
    if (res && res.startsWith('Error')) alert(res);
}

async function imgToBase64() {
    const src = document.getElementById('img2b64-src').value;
    if (!src) { alert('请先选择图片'); return; }
    const res = await pywebview.api.image_to_base64_save(src);
    if (res && res.startsWith('Error')) alert(res);
}

async function base64ToImg() {
    const data = document.getElementById('b64-input').value;
    if (!data) { alert('请输入Base64字符串'); return; }
    const res = await pywebview.api.base64_to_image(data);
    if (res && res.startsWith('Error')) alert(res);
}

// Generate Tools
async function generateQR() {
    const data = document.getElementById('qr-input').value;
    if (!data) return;
    const res = await pywebview.api.generate_qr(data);
    const container = document.getElementById('qr-result');
    container.innerHTML = '<img id="generated-qr-img" src="' + res + '" alt="QR Code">';
    document.getElementById('qr-result-container').style.display = 'flex';
}

async function saveQR() {
    const img = document.getElementById('generated-qr-img');
    if (!img) return;
    const res = await pywebview.api.save_image_from_base64(img.src, "qrcode.png");
    if (res && res.startsWith('Error')) alert(res);
}

async function generateUUIDs() {
    const count = parseInt(document.getElementById('uuid-count').value);
    const hyphen = document.getElementById('uuid-hyphen').checked;
    const upper = document.getElementById('uuid-upper').checked;
    const braces = document.getElementById('uuid-braces').checked;
    const res = await pywebview.api.generate_uuids(count, hyphen, upper, braces);
    document.getElementById('uuid-output').value = res;
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
        ["0000 1010", "012", "10", "0x0A", "LF", "Line Feed (换行)"],
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
});
