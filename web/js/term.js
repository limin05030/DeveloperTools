// ============================================================
// 终端功能模块 — 键盘映射、行内编辑、本地回显、历史记录、剪贴板
// ============================================================

// ---- 键盘 → 终端转义序列映射 ----
function _keyToTermData(e) {
    var key = e.key, ctrl = e.ctrlKey, alt = e.altKey, shift = e.shiftKey, meta = e.metaKey;

    // 忽略 IME 组合输入和纯修饰键
    if (e.isComposing || key === 'Dead' || key === 'Process') return null;
    if (key === 'Control' || key === 'Alt' || key === 'Shift' || key === 'Meta' ||
        key === 'CapsLock' || key === 'NumLock' || key === 'ScrollLock' ||
        key === 'Pause' || key === 'ContextMenu' || key === 'OS') return null;

    // 系统快捷键放行
    if (meta) return null;
    if (alt && (key === 'Tab' || key === 'Escape')) return null;
    if (ctrl && shift && (key === 'C' || key === 'c' || key === 'V' || key === 'v')) return null;
    if (ctrl && key === 'Insert') return null;
    if (shift && key === 'Insert') return null;

    // Ctrl 组合键 → ASCII 控制字符
    if (ctrl && !alt && !shift && !meta) {
        if (key === ' ' || key === 'Spacebar') return '\x00';
        if (key.length === 1) {
            var code = key.toUpperCase().charCodeAt(0);
            if (code >= 65 && code <= 90) return String.fromCharCode(code - 64);
            if (code === 219) return '\x1b';      // Ctrl+[ → ESC
            if (code === 220) return '\x1c';      // Ctrl+\
            if (code === 221) return '\x1d';      // Ctrl+]
            if (code === 54 || key === '^') return '\x1e';
            if (code === 189 || key === '-') return '\x1f';
        }
    }

    // Alt+字母 → ESC + 字母
    if (alt && !ctrl && !meta && key.length === 1) return '\x1b' + key;

    // 特殊功能键
    if (key === 'Enter' || key === 'Return') return '\r\n';
    if (key === 'Backspace') return '\x7f';
    if (key === 'Tab')       return '\t';
    if (key === 'Escape')    return '\x1b';
    if (key === 'Delete')    return '\x1b[3~';
    if (key === 'Insert')    return '\x1b[2~';
    if (key === 'Home')      return '\x1b[H';
    if (key === 'End')       return '\x1b[F';
    if (key === 'PageUp')    return '\x1b[5~';
    if (key === 'PageDown')  return '\x1b[6~';

    // 方向键
    if (key === 'ArrowUp')    return ctrl ? '\x1b[1;5A' : '\x1b[A';
    if (key === 'ArrowDown')  return ctrl ? '\x1b[1;5B' : '\x1b[B';
    if (key === 'ArrowRight') return ctrl ? '\x1b[1;5C' : '\x1b[C';
    if (key === 'ArrowLeft')  return ctrl ? '\x1b[1;5D' : '\x1b[D';

    // 功能键 F1-F12
    var fkeyMap = {
        'F1': '\x1bOP', 'F2': '\x1bOQ', 'F3': '\x1bOR', 'F4': '\x1bOS',
        'F5': '\x1b[15~', 'F6': '\x1b[17~', 'F7': '\x1b[18~', 'F8': '\x1b[19~',
        'F9': '\x1b[20~', 'F10': '\x1b[21~', 'F11': '\x1b[23~', 'F12': '\x1b[24~'
    };
    if (fkeyMap[key]) return fkeyMap[key];

    // 可打印单字符
    if (key.length === 1) return key;
    return null;
}

// ---- 行内编辑：重绘当前输入行 ----
// 提示符 + 缓冲区内容，光标定位到插入位置
function _redrawInput(term, tid) {
    var prompt = window._termSavedPrompt || '';
    var buf = window._termInputBuf[tid] || '';
    var pos = window._termInputPos[tid] || 0;
    var output = '\r' + prompt + buf + '\x1b[K';        // 回行首 + 写整行 + 清至行尾
    if (pos < buf.length) output += '\x1b[' + (buf.length - pos) + 'D';  // 光标左移
    term.write(output);
}

// 判断是否为本地编辑键（不发送到 cmd.exe）
function _isLocalEditKey(e) {
    var k = e.key;
    return k === 'ArrowLeft' || k === 'ArrowRight' || k === 'ArrowUp' || k === 'ArrowDown' ||
           k === 'Home' || k === 'End' || k === 'Delete';
}

// 处理本地编辑键和命令历史
function _handleLocalEdit(e, term, tid) {
    if (!window._termInputBuf) window._termInputBuf = {};
    if (!window._termInputPos) window._termInputPos = {};
    var buf = window._termInputBuf[tid] || '';
    var pos = (window._termInputPos[tid] !== undefined) ? window._termInputPos[tid] : buf.length;

    switch (e.key) {
        case 'ArrowLeft':
            if (pos > 0) { window._termInputPos[tid] = pos - 1; _redrawInput(term, tid); }
            return true;
        case 'ArrowRight':
            if (pos < buf.length) { window._termInputPos[tid] = pos + 1; _redrawInput(term, tid); }
            return true;
        case 'Home':
            if (pos > 0) { window._termInputPos[tid] = 0; _redrawInput(term, tid); }
            return true;
        case 'End':
            if (pos < buf.length) { window._termInputPos[tid] = buf.length; _redrawInput(term, tid); }
            return true;
        case 'Delete':
            if (pos < buf.length) {
                window._termInputBuf[tid] = buf.slice(0, pos) + buf.slice(pos + 1);
                _redrawInput(term, tid);
            }
            return true;

        // 命令历史：↑ 上一条，↓ 下一条
        case 'ArrowUp':
            if (!window._termHistory) window._termHistory = {};
            if (!window._termHistory[tid]) window._termHistory[tid] = [];
            if (!window._termHistPos) window._termHistPos = {};
            if (!window._termHistSave) window._termHistSave = {};
            var hist = window._termHistory[tid];
            if (hist.length === 0) return true;
            var hp = (window._termHistPos[tid] !== undefined) ? window._termHistPos[tid] : -1;
            if (hp === -1) window._termHistSave[tid] = buf;
            if (hp < hist.length - 1) {
                hp++;
                window._termHistPos[tid] = hp;
                window._termInputBuf[tid] = hist[hist.length - 1 - hp];
                window._termInputPos[tid] = window._termInputBuf[tid].length;
                _redrawInput(term, tid);
            }
            return true;

        case 'ArrowDown':
            if (!window._termHistory || !window._termHistory[tid]) return true;
            var hist2 = window._termHistory[tid];
            if (hist2.length === 0) return true;
            var hp2 = (window._termHistPos[tid] !== undefined) ? window._termHistPos[tid] : -1;
            if (hp2 > 0) {
                hp2--;
                window._termHistPos[tid] = hp2;
                window._termInputBuf[tid] = hist2[hist2.length - 1 - hp2];
                window._termInputPos[tid] = window._termInputBuf[tid].length;
                _redrawInput(term, tid);
            } else if (hp2 === 0) {
                window._termHistPos[tid] = -1;
                window._termInputBuf[tid] = window._termHistSave[tid] || '';
                window._termInputPos[tid] = window._termInputBuf[tid].length;
                _redrawInput(term, tid);
            }
            return true;
    }
    return false;
}

// ---- 本地回显 ----
// 管理输入缓冲区和本地回显。可打印字符、退格等只存本地，回车时一次性发送完整命令。
// 返回 'local-only' 表示数据已本地处理，不需再发送到后端。
function _localEcho(term, data, tid) {
    if (!data || data.length === 0) return;

    // 初始化
    if (!window._termInputBuf) window._termInputBuf = {};
    if (!window._termInputPos) window._termInputPos = {};
    if (window._termInputBuf[tid] === undefined) { window._termInputBuf[tid] = ''; window._termInputPos[tid] = 0; }
    var buf = window._termInputBuf[tid];
    var pos = window._termInputPos[tid];

    // 刷新待输出的行缓冲
    if (window._termLineBuf) {
        for (var key in window._termLineBuf) {
            if (window._termLineBuf[key] !== undefined) {
                var lb = window._termLineBuf[key];
                if (lb.endsWith('\r\n')) lb = lb.slice(0, -2); else if (lb.endsWith('\n')) lb = lb.slice(0, -1);
                term.write(lb); window._termLineBuf[key] = undefined;
            }
        }
    }
    if (window._termLineTimers) {
        for (var key in window._termLineTimers) { clearTimeout(window._termLineTimers[key]); delete window._termLineTimers[key]; }
    }

    // 可打印单字符 → 插入缓冲
    if (data.length === 1 && data.charCodeAt(0) >= 32 && data.charCodeAt(0) !== 127) {
        window._termInputBuf[tid] = buf.slice(0, pos) + data + buf.slice(pos);
        window._termInputPos[tid] = pos + 1;
        if (pos === buf.length) term.write(data); else _redrawInput(term, tid);  // 末尾追加不重绘
        return 'local-only';
    }

    // 退格
    if (data === '\x7f' || data === '\x08') {
        if (pos > 0) {
            window._termInputBuf[tid] = buf.slice(0, pos - 1) + buf.slice(pos);
            window._termInputPos[tid] = pos - 1;
            if (pos === buf.length) term.write('\b \b'); else _redrawInput(term, tid);
        }
        return 'local-only';
    }

    // 回车 → 发送完整命令
    if (data === '\r\n' || data === '\r') {
        if (buf.length === 0) term.write('\r\n'); else term.write('\r');
        var cmd = window._termInputBuf[tid];
        var lowerCmd = cmd.trim().toLowerCase();

        // cls / clear → 本地清屏
        if (lowerCmd === 'cls' || lowerCmd === 'clear') {
            term.clear();
            if (window._termLineBuf) window._termLineBuf[tid] = undefined;
            if (window._termLineTimers) { clearTimeout(window._termLineTimers[tid]); delete window._termLineTimers[tid]; }
            window._termInputBuf[tid] = ''; window._termInputPos[tid] = 0;
            _redrawInput(term, tid);
        } else {
            window._termOnDataCallbacks[tid](cmd + '\r\n');
        }

        // 保存命令历史
        if (cmd.length > 0) {
            if (!window._termHistory) window._termHistory = {};
            if (!window._termHistory[tid]) window._termHistory[tid] = [];
            var hist = window._termHistory[tid];
            if (hist.length === 0 || hist[hist.length - 1] !== cmd) hist.push(cmd);
            if (hist.length > 500) hist.shift();
            window._termHistPos = window._termHistPos || {};
            window._termHistPos[tid] = -1;
        }
        window._termInputBuf[tid] = ''; window._termInputPos[tid] = 0;
        return 'local-only';
    }

    // Tab
    if (data === '\t') {
        window._termInputBuf[tid] = buf.slice(0, pos) + '\t' + buf.slice(pos);
        window._termInputPos[tid] = pos + 1;
        if (pos === buf.length) term.write('\t'); else _redrawInput(term, tid);
        return 'local-only';
    }

    // 多字符粘贴
    if (data.length > 1) {
        window._termInputBuf[tid] = buf.slice(0, pos) + data + buf.slice(pos);
        window._termInputPos[tid] = pos + data.length;
        _redrawInput(term, tid);
        return 'local-only';
    }
}

// ---- 剪贴板操作 ----
function _termCopy(term) {
    var sel = term.getSelection(); if (!sel) return;
    navigator.clipboard.writeText(sel).catch(function () {
        var ta = document.createElement('textarea'); ta.value = sel;
        ta.style.cssText = 'position:fixed;left:-9999px;'; document.body.appendChild(ta);
        ta.select(); try { document.execCommand('copy'); } catch (e) { } ta.remove();
    });
}

function _termPaste(term, tid) {
    navigator.clipboard.readText().then(function (text) {
        if (text && window._termOnDataCallbacks[tid]) { window._termOnDataCallbacks[tid](text); _localEcho(term, text, tid); }
    }).catch(function () { });
}
