# -*- coding: utf-8 -*-
import ssl
import sys
import os
import re
import json
import base64
import urllib.parse
import urllib.request
import time
import certifi
from datetime import datetime, timezone, timedelta
import webview

# 以下重型模块已改为按需延迟导入，减少启动时间：
#   PIL (Image, ImageDraw) — 仅在图片处理方法中导入
#   qrcode                   — 仅在 generate_qr 中导入
#   zhconv                   — 仅在 encode_decode 中导入
#   bs4 (BeautifulSoup)      — 仅在 _fetch_android 和 format_data 中导入
#   hashlib, hmac            — 仅在 calc_hash / calc_file_hash 中导入
#   html, uuid, webbrowser   — 仅在对应方法中导入

class Api:
    def __init__(self, is_debug: bool=False):
        self._window = None
        self._debug = is_debug
        self._raw_uuids = []
        self._terms = {}        # id → TerminalSession
        self.APPLE_OFFSET = 978307200
        self.storage_dir = os.path.join(os.path.expanduser("~"), ".developer_tools")
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        # pillow_heif 改为按需加载（首次处理 HEIC 图片时）

    def set_window(self, window):
        self._window = window
    def open_url(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
            return self._success(True)
        except Exception as e:
            return self._error(e)

    def embed_browser_show_tab(self, tab_id, url):
        """切换/显示嵌入式浏览器的标签页"""
        try:
            from backend.embedded_browser import get_embedded_browser
            eb = get_embedded_browser()
            ok = eb.show_tab(tab_id, url)
            return self._success(ok)
        except Exception as e:
            return self._error(e)

    def embed_browser_hide(self):
        """隐藏嵌入式浏览器"""
        try:
            from backend.embedded_browser import get_embedded_browser
            eb = get_embedded_browser()
            eb.hide()
            return self._success(True)
        except Exception as e:
            return self._error(e)

    def embed_browser_go_back(self):
        """嵌入式浏览器后退"""
        try:
            from backend.embedded_browser import get_embedded_browser
            eb = get_embedded_browser()
            ok = eb.go_back()
            return self._success(ok)
        except Exception as e:
            return self._error(e)

    def embed_browser_go_forward(self):
        """嵌入式浏览器前进"""
        try:
            from backend.embedded_browser import get_embedded_browser
            eb = get_embedded_browser()
            ok = eb.go_forward()
            return self._success(ok)
        except Exception as e:
            return self._error(e)

    def embed_browser_reload(self):
        """嵌入式浏览器刷新"""
        try:
            from backend.embedded_browser import get_embedded_browser
            eb = get_embedded_browser()
            ok = eb.reload()
            return self._success(ok)
        except Exception as e:
            return self._error(e)

    def get_local_permissions(self, platform):
        try:
            path = os.path.join(self.storage_dir, f"{platform}_perms.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return self._success(json.load(f))
            return self._success(None)
        except Exception as e:
            return self._error(e)

    def fetch_permissions(self, platform):
        try:
            if platform == 'android':
                return self._fetch_android()

            return self._error("Unsupported platform")
        except Exception as e:
            return self._error(e)

    def _fetch_android(self):
        url = "https://developer.android.com/reference/android/Manifest.permission"
        try:
            from bs4 import BeautifulSoup
            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=context) as response:
                html_content = response.read().decode('utf-8')
            
            soup = BeautifulSoup(html_content, 'html.parser')
            permissions = {}

            # 第一步，获取权限和权限的描述
            trs = soup.find_all("tr", attrs={"data-version-added": True})
            for tr in trs:
                tds = tr.find_all("td")
                for td in tds:
                    code = td.find("code")
                    p = td.find("p")
                    if not code or not p:
                        continue

                    permission_name = code.get_text()
                    if not permission_name.isupper(): # 全部是大写的才是正确的权限名字
                        continue

                    desc = p.get_text().replace("\n", "").strip()
                    desc = re.sub(r' +', ' ', desc)  # 将连续的多个空格换成一个空格

                    # 去掉描述信息里关于 API 过时的相关描述
                    if 'This constant was deprecated in API level ' in desc:
                        desc = desc.split('.', maxsplit=1)[1]
                    if 'The API that used this permission is no longer functional.' in desc:
                        desc = desc.split("The API that used this permission is no longer functional.", maxsplit=1)[
                            1].strip()

                    permissions[permission_name] = {"name": permission_name, "desc": desc}
                    break

            # 第二步，获取权限的添加和废弃 API 级别、权限级别等信息
            perm_divs = soup.find_all("div", attrs={"data-version-added": True})
            for div in perm_divs:
                # 过滤掉有 id 的属性的 div
                if div.get("id"):
                    continue

                api_level_div = div.find("div", class_="api-level")
                if not api_level_div:
                    continue

                api_level_str = api_level_div.get_text().strip().replace("\n", "")
                deprecated_in_str = None
                deprecated_level = None
                if "Deprecated in" in api_level_str:
                    api_level_str, deprecated_in_str = api_level_str.split("Deprecated in", maxsplit=1)
                if "Added in API level" in api_level_str:
                    api_level = api_level_str.replace("Added in API level", "").strip()
                elif "Added in version" in api_level_str:
                    api_level = api_level_str.replace("Added in version", "").strip()
                else:
                    continue
                if deprecated_in_str:
                    deprecated_level = deprecated_in_str.strip().replace("API level", "").strip()

                h3 = div.find('h3', class_="api-name", recursive=False)
                p = div.find("p", recursive=False)
                if h3 and p:
                    name = h3.get_text().strip()
                    if name in permissions:
                        permissions[name]["added"] = api_level
                        permissions[name]["deprecated"] = deprecated_level
                        permission_level = 'normal'
                        for l in p.get_text().split("\n"):
                            if 'Protection level:' in l:
                                permission_level = l.strip().replace("Protection level:", "").strip()
                                break
                        permissions[name]["permission_level"] = permission_level
                else:
                    raise Exception(f"No permissions found for {api_level_str}")


            if permissions:
                # 开始翻译流程
                self._log("Translating descriptions...")
                cache = self._get_translation_cache()
                needs_save = False
                
                # 遍历翻译
                for name, info in permissions.items():
                    orig_desc = info.get('desc', '')
                    if orig_desc:
                        translated = self._translate_text(orig_desc, cache)
                        if translated != orig_desc:
                            info['desc'] = translated
                            needs_save = True
                
                if needs_save:
                    self._save_translation_cache(cache)
                self._log("Translation complete.")

                perms = list(permissions.values())

                self._save_to_local('android', perms)
                return self._success(perms)
            return self._error("No permissions found")
        except Exception as e:
            return self._error(f"Fetch failed: {str(e)}")



    def _save_to_local(self, platform, data):
        path = os.path.join(self.storage_dir, f"{platform}_perms.json")
        self._log(f"Saving permissions to {path}")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


    def _log(self, msg):
        if self._debug:
            print(f"[Backend API] {msg}")

    def _success(self, data):
        return {"success": True, "data": data}

    def _error(self, message):
        return {"success": False, "error": str(message)}

    def select_file(self, file_types=None):
        try:
            self._log("Opening select_file dialog...")
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types if file_types else ())
            if result and isinstance(result, (list, tuple)):
                return self._success(result[0])
            return self._success(result) if result else self._error("Cancelled")
        except Exception as e:
            self._log(f"Error in select_file: {str(e)}")
            return self._error(e)

    def save_file_api(self, filename, patterns):
        res = self.save_file(filename, patterns)
        if res: return self._success(res)
        return self._error('Cancelled')

    def save_file(self, filename, patterns):
        formats_to_try = []
        ft1 = []
        for desc, pat in patterns:
            ft1.append(desc); ft1.append(pat)
        formats_to_try.append(tuple(ft1))
        
        ft2 = []
        for desc, pat in patterns:
            ext = pat.split('.')[-1]
            ft2.append(desc); ft2.append(ext)
        formats_to_try.append(tuple(ft2))
        formats_to_try.append(None)

        last_error = None
        for ft in formats_to_try:
            try:
                result = self._window.create_file_dialog(
                    webview.SAVE_DIALOG, 
                    save_filename=filename, 
                    file_types=ft if ft else ()
                )
                if result and isinstance(result, (list, tuple)):
                    return result[0]
                return result
            except Exception as e:
                last_error = str(e)
                continue
        return None

    # --- Hash Tools ---
    def calc_hash(self, data, algo, is_hmac, key_str):
        try:
            import hashlib
            import hmac
            key = key_str.encode()
            actual_algo = "md5" if algo.startswith("md5") else algo
            h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
            h.update(data.encode('utf-8'))
            res = h.hexdigest()
            return self._success(res[8:24] if algo == "md5-16" else res)
        except Exception as e:
            return self._error(e)

    def calc_file_hash(self, path, algo, is_hmac, key_str):
        try:
            import hashlib
            import hmac
            if not os.path.isfile(path): return self._error("File not found")
            key = key_str.encode()
            actual_algo = "md5" if algo.startswith("md5") else algo
            h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            res = h.hexdigest()
            return self._success(res[8:24] if algo == "md5-16" else res)
        except Exception as e:
            return self._error(e)

    # --- Crypto Tools ---

    # ---- RC5 分组密码实现 (RC5-32/12/16) ----
    class _RC5Cipher:
        """RC5-32/12/16 分组密码：32位字、12轮、8字节块"""
        BLOCK_SIZE = 8
        ROUNDS = 12
        W = 32
        P = 0xB7E15163
        Q = 0x9E3779B9

        def __init__(self, key):
            U32 = lambda v: v & 0xFFFFFFFF
            ROTL = lambda v, n: U32((v << (n % 32)) | (v >> (32 - (n % 32))))
            ROTR = lambda v, n: U32((v >> (n % 32)) | (v << (32 - (n % 32))))

            # 将密钥转换为小端序 32 位字数组 L
            key_len = len(key)
            c = max(1, (key_len + 3) // 4)
            L = [0] * c
            for i in range(key_len - 1, -1, -1):
                L[i // 4] = U32((L[i // 4] << 8) | key[i])

            # 初始化 S 数组
            t = 2 * (self.ROUNDS + 1)
            S = [0] * t
            S[0] = self.P
            for i in range(1, t):
                S[i] = U32(S[i - 1] + self.Q)

            # 混合 S 和 L
            i = j = 0
            A = B = 0
            for _ in range(3 * max(t, c)):
                A = S[i] = ROTL(U32(S[i] + A + B), 3)
                B = L[j] = ROTL(U32(L[j] + A + B), (A + B) % 32)
                i = (i + 1) % t
                j = (j + 1) % c

            self.S = S
            self._ROTL = ROTL
            self._ROTR = ROTR
            self._U32 = U32

        def encrypt_block(self, block):
            """加密一个 8 字节块，返回 8 字节"""
            U32 = self._U32
            ROTL = self._ROTL
            A = int.from_bytes(block[0:4], 'little')
            B = int.from_bytes(block[4:8], 'little')
            S = self.S
            A = U32(A + S[0])
            B = U32(B + S[1])
            for i in range(1, self.ROUNDS + 1):
                A = U32(ROTL(A ^ B, B % 32) + S[2 * i])
                B = U32(ROTL(B ^ A, A % 32) + S[2 * i + 1])
            return A.to_bytes(4, 'little') + B.to_bytes(4, 'little')

        def decrypt_block(self, block):
            """解密一个 8 字节块，返回 8 字节"""
            U32 = self._U32
            ROTR = self._ROTR
            A = int.from_bytes(block[0:4], 'little')
            B = int.from_bytes(block[4:8], 'little')
            S = self.S
            for i in range(self.ROUNDS, 0, -1):
                B = U32(ROTR(U32(B - S[2 * i + 1]), A % 32) ^ A)
                A = U32(ROTR(U32(A - S[2 * i]), B % 32) ^ B)
            B = U32(B - S[1])
            A = U32(A - S[0])
            return A.to_bytes(4, 'little') + B.to_bytes(4, 'little')

    # ---- RC6 分组密码实现 (RC6-32/20/16) ----
    class _RC6Cipher:
        """RC6-32/20/16 分组密码：32位字、20轮、16字节块"""
        BLOCK_SIZE = 16
        ROUNDS = 20
        W = 32
        LG_W = 5
        P = 0xB7E15163
        Q = 0x9E3779B9

        def __init__(self, key):
            U32 = lambda v: v & 0xFFFFFFFF
            ROTL = lambda v, n: U32((v << (n % 32)) | (v >> (32 - (n % 32))))
            ROTR = lambda v, n: U32((v >> (n % 32)) | (v << (32 - (n % 32))))

            # 将密钥转换为小端序 32 位字数组 L
            key_len = len(key)
            c = max(1, (key_len + 3) // 4)
            L = [0] * c
            for i in range(key_len - 1, -1, -1):
                L[i // 4] = U32((L[i // 4] << 8) | key[i])

            # 初始化 S 数组: t = 2 * (r + 2) = 44
            t = 2 * (self.ROUNDS + 2)
            S = [0] * t
            S[0] = self.P
            for i in range(1, t):
                S[i] = U32(S[i - 1] + self.Q)

            # 混合 S 和 L
            i = j = 0
            A = B = 0
            for _ in range(3 * max(t, c)):
                A = S[i] = ROTL(U32(S[i] + A + B), 3)
                B = L[j] = ROTL(U32(L[j] + A + B), (A + B) % 32)
                i = (i + 1) % t
                j = (j + 1) % c

            self.S = S
            self._ROTL = ROTL
            self._ROTR = ROTR
            self._U32 = U32

        def encrypt_block(self, block):
            """加密一个 16 字节块，返回 16 字节"""
            U32 = self._U32
            ROTL = self._ROTL
            S = self.S
            A = int.from_bytes(block[0:4], 'little')
            B = int.from_bytes(block[4:8], 'little')
            C = int.from_bytes(block[8:12], 'little')
            D = int.from_bytes(block[12:16], 'little')
            B = U32(B + S[0])
            D = U32(D + S[1])
            for i in range(1, self.ROUNDS + 1):
                t = ROTL(U32(B * (2 * B + 1)), self.LG_W)
                u = ROTL(U32(D * (2 * D + 1)), self.LG_W)
                A = U32(ROTL(A ^ t, u % 32) + S[2 * i])
                C = U32(ROTL(C ^ u, t % 32) + S[2 * i + 1])
                A, B, C, D = B, C, D, A
            A = U32(A + S[2 * self.ROUNDS + 2])
            C = U32(C + S[2 * self.ROUNDS + 3])
            return A.to_bytes(4, 'little') + B.to_bytes(4, 'little') + C.to_bytes(4, 'little') + D.to_bytes(4, 'little')

        def decrypt_block(self, block):
            """解密一个 16 字节块，返回 16 字节"""
            U32 = self._U32
            ROTR = self._ROTR
            ROTL = self._ROTL
            S = self.S
            A = int.from_bytes(block[0:4], 'little')
            B = int.from_bytes(block[4:8], 'little')
            C = int.from_bytes(block[8:12], 'little')
            D = int.from_bytes(block[12:16], 'little')
            C = U32(C - S[2 * self.ROUNDS + 3])
            A = U32(A - S[2 * self.ROUNDS + 2])
            for i in range(self.ROUNDS, 0, -1):
                A, B, C, D = D, A, B, C
                u = ROTL(U32(D * (2 * D + 1)), self.LG_W)
                t = ROTL(U32(B * (2 * B + 1)), self.LG_W)
                C = U32(ROTR(U32(C - S[2 * i + 1]), t % 32) ^ u)
                A = U32(ROTR(U32(A - S[2 * i]), u % 32) ^ t)
            D = U32(D - S[1])
            B = U32(B - S[0])
            return A.to_bytes(4, 'little') + B.to_bytes(4, 'little') + C.to_bytes(4, 'little') + D.to_bytes(4, 'little')

    # ---- 通用分组密码模式处理器 ----
    def _raw_block_crypt(self, data_bytes, operation, mode, encrypt_fn, decrypt_fn,
                         block_size, key, iv, padding):
        """为自实现的分组密码提供 ECB/CBC/CFB/OFB/CTR 模式支持"""
        from Crypto.Util.Padding import pad, unpad

        # 重用 _crypto_core 中的填充函数
        def _crypto_pad(d, bs, style):
            if style == 'none': return d
            if style == 'zero':
                n = bs - (len(d) % bs)
                return d + b'\x00' * (n if n else bs)
            if style == 'iso10126':
                n = bs - (len(d) % bs)
                return d + os.urandom((n if n else bs) - 1) + bytes([n if n else bs])
            return pad(d, bs, style=style)

        def _crypto_unpad(d, bs, style):
            if style == 'none': return d
            if style == 'zero': return d.rstrip(b'\x00')
            if style == 'iso10126':
                n = d[-1]
                if n < 1 or n > bs:
                    raise ValueError("无效的 ISO 10126 填充")
                return d[:-n]
            return unpad(d, bs, style=style)

        needs_padding = mode in ('ECB', 'CBC', 'CFB', 'OFB')
        if operation == 'encrypt' and needs_padding:
            data_bytes = _crypto_pad(data_bytes, block_size, padding)

        result = bytearray()

        if mode == 'ECB':
            for i in range(0, len(data_bytes), block_size):
                chunk = data_bytes[i:i + block_size]
                result.extend(encrypt_fn(chunk) if operation == 'encrypt' else decrypt_fn(chunk))

        elif mode == 'CBC':
            if not iv or len(iv) != block_size:
                raise ValueError(f"CBC 模式需要 {block_size} 字节 IV")
            prev = iv
            for i in range(0, len(data_bytes), block_size):
                chunk = data_bytes[i:i + block_size]
                if operation == 'encrypt':
                    xored = bytes(c ^ p for c, p in zip(chunk, prev))
                    prev = encrypt_fn(xored)
                    result.extend(prev)
                else:
                    dec = decrypt_fn(chunk)
                    result.extend(bytes(d ^ p for d, p in zip(dec, prev)))
                    prev = chunk

        elif mode == 'CFB':
            if not iv or len(iv) != block_size:
                raise ValueError(f"CFB 模式需要 {block_size} 字节 IV")
            prev = iv
            for i in range(0, len(data_bytes), block_size):
                chunk = data_bytes[i:i + block_size]
                enc_prev = encrypt_fn(prev)
                if operation == 'encrypt':
                    prev = bytes(c ^ e for c, e in zip(chunk, enc_prev))
                    result.extend(prev)
                else:
                    result.extend(bytes(c ^ e for c, e in zip(chunk, enc_prev)))
                    prev = chunk

        elif mode == 'OFB':
            if not iv or len(iv) != block_size:
                raise ValueError(f"OFB 模式需要 {block_size} 字节 IV")
            prev = iv
            for i in range(0, len(data_bytes), block_size):
                chunk = data_bytes[i:i + block_size]
                prev = encrypt_fn(prev)
                result.extend(bytes(c ^ p for c, p in zip(chunk, prev)))

        elif mode == 'CTR':
            # 将 IV 拆分为 nonce 和 counter：前 block_size/2 为 nonce，后 block_size/2 为 counter
            half = block_size // 2
            if iv and len(iv) >= half:
                nonce = iv[:half]
                ctr = int.from_bytes(iv[half:], 'big')
            else:
                nonce = b'\x00' * half
                ctr = 0
            for offset in range(0, len(data_bytes), block_size):
                ctr_block = nonce + ctr.to_bytes(block_size - half, 'big')
                keystream = encrypt_fn(ctr_block)
                chunk = data_bytes[offset:offset + block_size]
                result.extend(bytes(c ^ k for c, k in zip(chunk, keystream)))
                ctr += 1

        else:
            raise ValueError(f"不支持的模式: {mode}")

        result_bytes = bytes(result)

        if operation == 'decrypt' and needs_padding:
            result_bytes = _crypto_unpad(result_bytes, block_size, padding)

        return result_bytes

    @staticmethod
    def _rabbit_crypt(data, key, iv):
        """Rabbit 流密码 (RFC 4503)，加解密相同"""
        if len(key) != 16:
            raise ValueError("Rabbit 密钥必须是 16 字节 (32 个十六进制字符)")
        if iv is not None and len(iv) != 8:
            raise ValueError("Rabbit IV 必须是 8 字节 (16 个十六进制字符)")

        U32 = lambda v: v & 0xFFFFFFFF
        ROTL = lambda v, n: U32((v << n) | (v >> (32 - n)))

        class _RS:
            def __init__(self):
                self.x = [0] * 8
                self.c = [0] * 8
                self.carry = 0

            def _counter(self):
                A = [0x4D34D34D, 0xD34D34D3, 0x34D34D34, 0x4D34D34D,
                     0xD34D34D3, 0x34D34D34, 0x4D34D34D, 0xD34D34D3]
                for j in range(8):
                    s = U32(self.c[j] + A[j] + self.carry)
                    self.carry = 1 if s < self.c[j] + (1 if j == 0 else 0) else 0
                    self.c[j] = s

            def next_state(self):
                self._counter()
                g = [0] * 8
                for j in range(8):
                    s = U32(self.x[j] + self.c[j])
                    sq = U32((s * s) ^ ((s * s) >> 32))
                    g[j] = U32(sq ^ (sq >> 32))
                nx = [0] * 8
                nx[0] = U32(g[0] + ROTL(g[7], 16) + ROTL(g[6], 16))
                nx[1] = U32(g[1] + ROTL(g[0],  8) + g[7])
                nx[2] = U32(g[2] + ROTL(g[1], 16) + ROTL(g[0], 16))
                nx[3] = U32(g[3] + ROTL(g[2],  8) + g[1])
                nx[4] = U32(g[4] + ROTL(g[3], 16) + ROTL(g[2], 16))
                nx[5] = U32(g[5] + ROTL(g[4],  8) + g[3])
                nx[6] = U32(g[6] + ROTL(g[5], 16) + ROTL(g[4], 16))
                nx[7] = U32(g[7] + ROTL(g[6],  8) + g[5])
                self.x = nx

            def extract(self):
                s = [0] * 16
                s[0]  = U32(self.x[0]) >> 16;     s[1]  = self.x[0] & 0xFFFF
                s[2]  = self.x[1] >> 16;           s[3]  = self.x[1] & 0xFFFF
                s[4]  = self.x[2] >> 16;           s[5]  = self.x[2] & 0xFFFF
                s[6]  = self.x[3] >> 16;           s[7]  = self.x[3] & 0xFFFF
                s[8]  = U32(self.x[4]) >> 16;      s[9]  = self.x[4] & 0xFFFF
                s[10] = self.x[5] >> 16;           s[11] = self.x[5] & 0xFFFF
                s[12] = self.x[6] >> 16;           s[13] = self.x[6] & 0xFFFF
                s[14] = self.x[7] >> 16;           s[15] = self.x[7] & 0xFFFF
                s[0]  ^= self.x[4] >> 16;          s[1]  ^= self.x[4] & 0xFFFF
                s[2]  ^= self.x[5] >> 16;          s[3]  ^= self.x[5] & 0xFFFF
                s[4]  ^= self.x[6] >> 16;          s[5]  ^= self.x[6] & 0xFFFF
                s[6]  ^= self.x[7] >> 16;          s[7]  ^= self.x[7] & 0xFFFF
                s[8]  ^= self.x[0] >> 16;          s[9]  ^= self.x[0] & 0xFFFF
                s[10] ^= self.x[1] >> 16;          s[11] ^= self.x[1] & 0xFFFF
                s[12] ^= self.x[2] >> 16;          s[13] ^= self.x[2] & 0xFFFF
                s[14] ^= self.x[3] >> 16;          s[15] ^= self.x[3] & 0xFFFF
                return bytes([b & 0xFF for v in s for b in [v & 0xFF, (v >> 8) & 0xFF]])

        # ---- Key Setup Scheme ----
        st = _RS()
        kw = lambda i: U32((key[(i * 2 + 1) % 16] << 8) | key[(i * 2) % 16])
        k = [kw(i) for i in range(8)]
        st.x = [
            U32(k[0] | (k[3] << 16)), U32(k[5] | (k[2] << 16)),
            U32(k[4] | (k[7] << 16)), U32(k[1] | (k[6] << 16)),
            U32(k[6] | (k[1] << 16)), U32(k[3] | (k[0] << 16)),
            U32(k[2] | (k[5] << 16)), U32(k[7] | (k[4] << 16)),
        ]
        st.c = [
            ROTL(k[4], 16), U32(k[1] | (k[6] << 16)),
            ROTL(k[5], 16), U32(k[3] | (k[0] << 16)),
            ROTL(k[2], 16), U32(k[7] | (k[4] << 16)),
            ROTL(k[7], 16), U32(k[5] | (k[2] << 16)),
        ]

        # ---- IV Setup Scheme ----
        if iv:
            i0 = int.from_bytes(iv[0:4], 'little')
            i1 = int.from_bytes(iv[4:8], 'little')
            st.c[0] ^= i0; st.c[1] ^= i1
            st.c[2] ^= U32((i0 >> 16) | (i1 & 0xFFFF0000))
            st.c[3] ^= U32((i1 << 16) | (i0 & 0xFFFF))
            st.c[4] ^= i0; st.c[5] ^= i1
            st.c[6] ^= U32((i0 >> 16) | (i1 & 0xFFFF0000))
            st.c[7] ^= U32((i1 << 16) | (i0 & 0xFFFF))
            for _ in range(4):
                st.next_state()

        # ---- 生成密钥流 + XOR ----
        result = bytearray()
        for offset in range(0, len(data), 16):
            st.next_state()
            ks = st.extract()
            chunk = data[offset:offset + 16]
            for j in range(len(chunk)):
                result.append(chunk[j] ^ ks[j])
        return bytes(result)

    def _crypto_core(self, data_bytes, algorithm, mode, key_hex, iv_hex, operation, padding):
        """核心加解密逻辑：输入 bytes → 输出 bytes"""
        from Crypto.Cipher import AES, DES, DES3, ARC2

        # ---- 解析密钥 / IV ----
        try:
            key = bytes.fromhex(key_hex)
        except Exception:
            raise ValueError("密钥格式错误，请输入十六进制字符串")

        iv = bytes.fromhex(iv_hex) if iv_hex else None

        # ---- 流密码 (无需模式和填充) ----
        if algorithm == 'RC4':
            if len(key) == 0:
                raise ValueError("RC4 需要密钥")
            from Crypto.Cipher import ARC4
            return ARC4.new(key).encrypt(data_bytes)

        if algorithm == 'ChaCha20':
            if len(key) != 32:
                raise ValueError("ChaCha20 密钥必须是 32 字节 (64 个十六进制字符)")
            from Crypto.Cipher import ChaCha20
            nonce = iv[:8] if iv and len(iv) >= 8 else b'\x00' * 8
            return ChaCha20.new(key=key, nonce=nonce).encrypt(data_bytes)

        if algorithm == 'XOR':
            if len(key) == 0:
                raise ValueError("XOR 需要密钥")
            return bytes([data_bytes[i] ^ key[i % len(key)] for i in range(len(data_bytes))])

        if algorithm == 'Rabbit':
            return self._rabbit_crypt(data_bytes, key, iv)

        # ---- 自实现分组密码 (RC5 / RC6)：通过 _raw_block_crypt 处理模式 ----
        if algorithm == 'RC5':
            if len(key) == 0:
                raise ValueError("RC5 需要密钥")
            cipher = self._RC5Cipher(key)
            return self._raw_block_crypt(
                data_bytes, operation, mode,
                cipher.encrypt_block, cipher.decrypt_block,
                self._RC5Cipher.BLOCK_SIZE, key, iv, padding
            )

        if algorithm == 'RC6':
            if len(key) == 0:
                raise ValueError("RC6 需要密钥")
            cipher = self._RC6Cipher(key)
            return self._raw_block_crypt(
                data_bytes, operation, mode,
                cipher.encrypt_block, cipher.decrypt_block,
                self._RC6Cipher.BLOCK_SIZE, key, iv, padding
            )

        # ---- 分组密码 (pycryptodome) ----
        from Crypto.Util.Padding import pad, unpad

        def _crypto_pad(d, bs, style):
            if style == 'none': return d
            if style == 'zero':
                n = bs - (len(d) % bs)
                return d + b'\x00' * (n if n else bs)
            if style == 'iso10126':
                n = bs - (len(d) % bs)
                return d + os.urandom((n if n else bs) - 1) + bytes([n if n else bs])
            return pad(d, bs, style=style)

        def _crypto_unpad(d, bs, style):
            if style == 'none': return d
            if style == 'zero': return d.rstrip(b'\x00')
            if style == 'iso10126':
                n = d[-1]
                if n < 1 or n > bs:
                    raise ValueError("无效的 ISO 10126 填充")
                return d[:-n]
            return unpad(d, bs, style=style)

        block_size = 16
        if algorithm.startswith('AES'):
            block_size = 16
            expected = {'AES-128': 16, 'AES-192': 24, 'AES-256': 32}.get(algorithm, 16)
            if len(key) != expected:
                raise ValueError(f"{algorithm} 密钥必须是 {expected} 字节 ({expected * 2} 个十六进制字符)")
            algo_cls = AES
        elif algorithm == 'DES':
            block_size = 8
            if len(key) != 8:
                raise ValueError("DES 密钥必须是 8 字节 (16 个十六进制字符)")
            algo_cls = DES
        elif algorithm == '3DES':
            block_size = 8
            if len(key) not in (16, 24):
                raise ValueError("3DES 密钥必须是 16 或 24 字节")
            algo_cls = DES3
        elif algorithm == 'RC2':
            block_size = 8
            if len(key) == 0:
                raise ValueError("RC2 需要密钥")
            algo_cls = ARC2
        else:
            raise ValueError(f"不支持的算法: {algorithm}")

        if mode == 'ECB':
            cipher = algo_cls.new(key, algo_cls.MODE_ECB)
        elif mode == 'CBC':
            if not iv or len(iv) != block_size:
                raise ValueError(f"CBC 模式需要 {block_size} 字节 IV")
            cipher = algo_cls.new(key, algo_cls.MODE_CBC, iv=iv)
        elif mode == 'CFB':
            if not iv or len(iv) != block_size:
                raise ValueError(f"CFB 模式需要 {block_size} 字节 IV")
            cipher = algo_cls.new(key, algo_cls.MODE_CFB, iv=iv)
        elif mode == 'OFB':
            if not iv or len(iv) != block_size:
                raise ValueError(f"OFB 模式需要 {block_size} 字节 IV")
            cipher = algo_cls.new(key, algo_cls.MODE_OFB, iv=iv)
        elif mode == 'CTR':
            nl = 8 if algorithm.startswith('AES') else 4
            nonce = iv[:nl] if iv and len(iv) >= nl else b'\x00' * nl
            cipher = algo_cls.new(key, algo_cls.MODE_CTR, nonce=nonce)
        elif mode == 'GCM':
            if not algorithm.startswith('AES'):
                raise ValueError("GCM 模式仅支持 AES")
            nonce = iv[:12] if iv and len(iv) >= 12 else b'\x00' * 12
            cipher = algo_cls.new(key, algo_cls.MODE_GCM, nonce=nonce)
        else:
            raise ValueError(f"不支持的模式: {mode}")

        needs_padding = mode in ('ECB', 'CBC', 'CFB', 'OFB')
        if operation == 'encrypt':
            if needs_padding:
                data_bytes = _crypto_pad(data_bytes, block_size, padding)
            return cipher.encrypt(data_bytes)
        else:
            result_bytes = cipher.decrypt(data_bytes)
            if needs_padding:
                result_bytes = _crypto_unpad(result_bytes, block_size, padding)
            return result_bytes

    def crypto_symmetric(self, data, algorithm, mode, key_hex, iv_hex, operation, input_fmt, output_fmt, padding='pkcs7'):
        """对称加密/解密（文本模式）"""
        try:
            # 输入解析
            if operation == 'encrypt':
                data_bytes = data.encode('utf-8')
            else:
                if input_fmt == 'hex':
                    data_bytes = bytes.fromhex(data)
                elif input_fmt == 'base64':
                    data_bytes = base64.b64decode(data)
                else:
                    return self._error("不支持的输入格式")

            result_bytes = self._crypto_core(data_bytes, algorithm, mode, key_hex, iv_hex, operation, padding)

            # 输出格式化
            if operation == 'encrypt':
                if output_fmt == 'hex':
                    result = result_bytes.hex()
                elif output_fmt == 'base64':
                    result = base64.b64encode(result_bytes).decode()
                else:
                    return self._error("不支持的输出格式")
            else:
                try:
                    result = result_bytes.decode('utf-8')
                except Exception:
                    result = result_bytes.hex()

            return self._success(result)
        except ImportError:
            return self._error("请先安装 pycryptodome: pip install pycryptodome")
        except Exception as e:
            msg = str(e)
            translations = {
                'Data must be padded to ': '块加密模式要求数据长度是 ',
                ' byte boundary in CBC mode': ' 字节的整数倍（CBC 模式）',
                ' byte boundary in ECB mode': ' 字节的整数倍（ECB 模式）',
                'Data must be aligned to block boundary in ECB mode': 'ECB 模式要求数据长度是块大小的整数倍',
                'Padding is incorrect.': '填充校验失败，请检查密钥或密文是否正确',
                'PKCS#7 padding is incorrect.': 'PKCS7 填充校验失败，请检查密钥或密文是否正确',
                'Invalid ISO 10126 padding': '无效的 ISO 10126 填充',
            }
            for eng, chn in translations.items():
                msg = msg.replace(eng, chn)
            return self._error(msg)

    def crypto_file(self, src_path, algorithm, mode, key_hex, iv_hex, operation, padding='pkcs7'):
        """对称加密/解密（文件模式）：读取文件 → 加解密 → 弹窗选择保存路径"""
        try:
            if not os.path.isfile(src_path):
                return self._error("文件不存在")

            with open(src_path, 'rb') as f:
                data_bytes = f.read()

            result_bytes = self._crypto_core(data_bytes, algorithm, mode, key_hex, iv_hex, operation, padding)

            # 弹窗选择保存路径
            base_name = os.path.basename(src_path)
            suffix = '.enc' if operation == 'encrypt' else '.dec'
            save_path = self.save_file(base_name + suffix, [("All files", "*.*")])
            if not save_path:
                return self._error("已取消")

            with open(save_path, 'wb') as f:
                f.write(result_bytes)

            return self._success("保存成功")
        except ImportError:
            return self._error("请先安装 pycryptodome: pip install pycryptodome")
        except Exception as e:
            msg = str(e)
            translations = {
                'Data must be padded to ': '块加密模式要求数据长度是 ',
                ' byte boundary in CBC mode': ' 字节的整数倍（CBC 模式）',
                ' byte boundary in ECB mode': ' 字节的整数倍（ECB 模式）',
                'Padding is incorrect.': '填充校验失败，请检查密钥或密文是否正确',
            }
            for eng, chn in translations.items():
                msg = msg.replace(eng, chn)
            return self._error(msg)

    def crypto_generate_bytes(self, size):
        """生成指定长度的随机字节（返回十六进制字符串）"""
        try:
            import secrets
            return self._success(secrets.token_bytes(size).hex())
        except Exception as e:
            return self._error(str(e))

    def crypto_read_file(self, path):
        """读取文件内容并返回十六进制字符串"""
        try:
            if not os.path.isfile(path):
                return self._error("文件不存在")
            with open(path, 'rb') as f:
                return self._success(f.read().hex())
        except Exception as e:
            return self._error(str(e))

    # --- Encode Tools ---
    def encode_decode(self, data, action):
        try:
            import html
            import zhconv
            if action == "b64_encode": res = base64.b64encode(data.encode()).decode()
            elif action == "b64_decode":
                try:
                    res = base64.b64decode(data.encode()).decode()
                except Exception:
                    return self._error("无效的 Base64 编码字符串或非文本内容")
            elif action == "url_encode": res = urllib.parse.quote(data, safe='/:?=&')
            elif action == "url_decode": res = urllib.parse.unquote(data)
            elif action == "utf8_encode": res = "".join([f"\\x{b:02x}" for b in data.encode('utf-8')])
            elif action == "utf8_decode": res = bytes.fromhex(data.replace("\\x", "")).decode('utf-8')
            elif action == "unicode_encode": res = data.encode('unicode_escape').decode('ascii')
            elif action == "unicode_decode": res = data.encode().decode('unicode_escape')
            elif action == "html_escape": res = html.escape(data)
            elif action == "html_unescape": res = html.unescape(data)
            elif action == "utf8_to_utf16": res = data.encode('utf-8').decode('utf-8').encode('utf-16-le').hex()
            elif action == "utf16_to_utf8": res = bytes.fromhex(data).decode('utf-16-le')
            elif action == "utf8_to_hex": res = data.encode('utf-8').hex()
            elif action == "hex_to_utf8": res = bytes.fromhex(data).decode('utf-8')
            elif action == "upper": res = data.upper()
            elif action == "lower": res = data.lower()
            elif action == "swap": res = data.swapcase()
            elif action == "traditional": res = zhconv.convert(data, 'zh-hant')
            elif action == "simplified": res = zhconv.convert(data, 'zh-hans')
            else: return self._error("Unknown action")
            return self._success(res)
        except Exception as e:
            self._log(e)
            return self._error(e)

    # --- Format Tools ---
    def format_data(self, data, fmt_type):
        try:
            if fmt_type == "json_format":
                res = json.dumps(json.loads(data), indent=4, ensure_ascii=False)
            elif fmt_type == "json_compress":
                res = json.dumps(json.loads(data), separators=(',', ':'), ensure_ascii=False)
            elif fmt_type in ("html_format", "html_xml"):
                from bs4 import BeautifulSoup, formatter
                is_xml = data.startswith("<?xml") or ("<" in data and not data.lower().startswith("<!doctype html"))
                soup = BeautifulSoup(data, "xml" if is_xml else "html.parser")
                res = soup.prettify(formatter=formatter.HTMLFormatter(indent=4))
            elif fmt_type == "html_compress":
                res = self._html_compress(data)
            elif fmt_type == "css_format":
                res = self._css_format(data)
            elif fmt_type == "css_compress":
                res = self._css_compress(data)
            elif fmt_type == "js_format":
                res = self._js_format(data)
            elif fmt_type == "js_compress":
                res = self._js_compress(data)
            elif fmt_type == "lua_compress":
                res = self._lua_compress(data)
            else: return self._error("Unknown format type")
            return self._success(res)
        except Exception as e:
            return self._error(e)

    def _html_compress(self, data):
        # 1. 移除注释
        data = re.sub(r'<!--.*?-->', '', data, flags=re.DOTALL)
        # 2. 移除标签间的空白
        data = re.sub(r'>\s+<', '><', data)
        # 3. 移除属性 = 周围的空格
        data = re.sub(r'\s*=\s*', '=', data)
        # 4. 压缩连续空白为一个空格
        data = re.sub(r'\s+', ' ', data)
        # 5. 移除 < 后的空格
        data = re.sub(r'<\s+', '<', data)
        # 6. 特别处理：移除 /> 和 > 前的空格，但保留属性间的一个空格
        data = re.sub(r'\s+/>', '/>', data)
        data = re.sub(r'\s+>', '>', data)
        return data.strip()

    def _protect_strings(self, data, lang='js'):
        """Replace string literals with placeholders to protect them from transformations."""
        if lang == 'js':
            pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`'
        elif lang == 'css':
            pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
        elif lang == 'lua':
            pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\[(=*)\[.*?\]\1\]'
        else:
            return data, []

        strings = []
        def _replace(m):
            strings.append(m.group(0))
            return f'\x00PROT{len(strings) - 1}\x00'

        protected = re.sub(pattern, _replace, data, flags=re.DOTALL)
        return protected, strings

    def _restore_strings(self, data, strings):
        """Restore string literals from placeholders."""
        for i, s in enumerate(strings):
            data = data.replace(f'\x00PROT{i}\x00', s)
        return data

    def _css_format(self, data):
        # 简单实现：每个规则换行，大括号缩进
        # 先保护字符串，防止其中的 { } ; , 被误替换
        data, strings = self._protect_strings(data, 'css')
        d = data.replace('{', ' {\n').replace('}', '\n}\n').replace(';', ';\n').replace(',', ', ')
        lines = d.split('\n')
        indent, formatted = 0, []
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith('}'): indent -= 1
            formatted.append("    " * max(0, indent) + line)
            if line.endswith('{'): indent += 1
            if line == '}': formatted.append("") # 规则间增加空行
        result = '\n'.join(formatted).strip()
        return self._restore_strings(result, strings)

    def _css_compress(self, data):
        # 先保护字符串，防止其中的注释标记被误删
        data, strings = self._protect_strings(data, 'css')
        # 移除注释
        data = re.sub(r'/\*.*?\*/', '', data, flags=re.DOTALL)
        # 移除换行和多余空格
        data = re.sub(r'\s+', ' ', data)
        # 移除符号周围的空格
        data = re.sub(r'\s*([{:;,])\s*', r'\1', data)
        return self._restore_strings(data.strip(), strings)

    def _js_format(self, code):
        # 先保护字符串，防止其中的 { } ; 被误替换
        code, strings = self._protect_strings(code, 'js')
        c = code.replace('{', ' {\n').replace('}', '\n}\n').replace(';', ';\n')
        c = re.sub(r'\n\s*\n', '\n', c)
        lines = c.split('\n')
        indent, formatted = 0, []
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith('}'): indent -= 1
            formatted.append("    " * max(0, indent) + line)
            if line.endswith('{'): indent += 1
        result = '\n'.join(formatted)
        return self._restore_strings(result, strings)

    def _js_compress(self, code):
        # 先保护字符串，防止其中的 // 和 /* */ 被误删
        code, strings = self._protect_strings(code, 'js')
        # 移除单行注释
        code = re.sub(r'//.*', '', code)
        # 移除多行注释
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # 移除换行和连续空格
        code = re.sub(r'\s+', ' ', code)
        # 移除操作符周围的空格 (优化)
        code = re.sub(r'\s*([{}()\[\]=+\-*/%&|^<>!?:;,])\s*', r'\1', code)
        return self._restore_strings(code.strip(), strings)

    def _lua_compress(self, code):
        # 先保护字符串，防止其中的 -- 被误删
        code, strings = self._protect_strings(code, 'lua')
        # 1. 移除多行注释 --[[ ]]
        code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
        # 2. 移除单行注释 --
        code = re.sub(r'--.*', '', code)
        # 3. 压缩空白
        code = re.sub(r'\s+', ' ', code)
        # 4. 移除操作符周围空格
        code = re.sub(r'\s*([{}()\[\]=+\-*/%#^<>~:;,])\s*', r'\1', code)
        return self._restore_strings(code.strip(), strings)

    # --- Base Conversion Tools ---
    def convert_base(self, data, from_base, to_base):
        try:
            # 去除可能的前缀和空白
            data = data.strip()
            fb, tb = int(from_base), int(to_base)
            
            # 先统一转换为 10 进制整数
            # 允许 0x, 0b, 0o 等 Python 自带前缀处理，但由于指定了进制，主要是靠 base 参数
            val = int(data, fb)
            
            if tb == 10:
                res = str(val)
            elif tb == 2:
                res = bin(val)[2:]
            elif tb == 8:
                res = oct(val)[2:]
            elif tb == 16:
                res = hex(val)[2:].upper()
            else:
                # 通用的任意进制转换 (支持 2-36)
                res = self._int_to_base(val, tb)
            
            return self._success(res)
        except Exception as e:
            return self._error(f"转换失败: {str(e)}")

    def _int_to_base(self, n, base):
        digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if n == 0:
            return "0"
        res = ""
        while n > 0:
            res = digits[n % base] + res
            n //= base
        return res

    # --- Time Tools ---
    def get_current_time(self, tz_offset):
        now = time.time()
        tz = timezone(timedelta(hours=tz_offset))
        dt_str = datetime.fromtimestamp(now, tz=tz).strftime("%Y-%m-%d %H:%M:%S.%f")
        return self._success({"ts": int(now * 1000), "date": dt_str[:-3]})

    def ts_to_date(self, ts_str, tz_offset, is_ios):
        try:
            ts = float(ts_str)
            if is_ios: ts += self.APPLE_OFFSET
            show_ms = ts > 10**11 or "." in ts_str
            if ts > 10**11: ts /= 1000.0
            tz = timezone(timedelta(hours=tz_offset))
            dt = datetime.fromtimestamp(ts, tz=tz)
            fmt = "%Y-%m-%d %H:%M:%S.%f" if show_ms else "%Y-%m-%d %H:%M:%S"
            res = dt.strftime(fmt)
            return self._success(res[:-3] if show_ms else res)
        except Exception as e:
            return self._error(e)

    def date_to_ts(self, date_str, tz_offset, is_ios):
        try:
            fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in date_str else "%Y-%m-%d %H:%M:%S"
            dt = datetime.strptime(date_str, fmt)
            tz = timezone(timedelta(hours=tz_offset))
            unix_ts = dt.replace(tzinfo=tz).timestamp()
            if is_ios:
                unix_ts -= self.APPLE_OFFSET
                res = f"{unix_ts:.3f}".rstrip('0').rstrip('.')
            else:
                res = str(int(unix_ts * 1000)) if "." in date_str else str(int(unix_ts))
            return self._success(res)
        except Exception as e:
            return self._error(e)

    # --- Generation Tools ---
    def generate_qr(self, data):
        try:
            import qrcode
            from io import BytesIO
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return self._success(f"data:image/png;base64,{img_str}")
        except Exception as e:
            return self._error(e)

    def generate_uuids(self, count, hyphen, upper, braces):
        try:
            import uuid
            self._raw_uuids = [str(uuid.uuid4()) for _ in range(int(count))]
            return self._success(self.format_uuids(hyphen, upper, braces))
        except Exception as e:
            return self._error(e)

    def decode_qr(self, file_path):
        try:
            import zxingcpp
        except ImportError:
            return self._error("缺失 zxing-cpp 库，请运行 'pip install zxing-cpp' 安装。")
            
        try:
            from PIL import Image
            if not os.path.exists(file_path):
                return self._error("文件不存在")
            img = Image.open(file_path)
            results = zxingcpp.read_barcodes(img)
            if not results:
                return self._error("未检测到二维码")
            
            decoded_texts = [r.text for r in results]
            return self._success("\n".join(decoded_texts))
        except Exception as e:
            return self._error(f"识别失败: {str(e)}")

    def format_uuids(self, hyphen, upper, braces):
        if not self._raw_uuids: return ""
        results = []
        for u in self._raw_uuids:
            p = u
            if not hyphen: p = p.replace("-", "")
            if upper: p = p.upper()
            if braces: p = "{" + p + "}"
            results.append(p)
        return "\n".join(results)

    def format_uuids_api(self, hyphen, upper, braces):
        return self._success(self.format_uuids(hyphen, upper, braces))

    # --- Image Tools ---
    def get_image_info(self, src):
        try:
            from PIL import Image
            with Image.open(src) as img:
                return self._success({"width": img.width, "height": img.height}) 
        except Exception as e: 
            return self._error(e) 

    def read_file_content_api(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return self._success(f.read())
        except Exception as e:
            return self._error(e)

    def read_text_file(self): 
        res = self.select_file() 
        if not res["success"]: return res
        path = res["data"]
        try: 
            with open(path, "r", encoding="utf-8") as f: 
                return self._success(f.read()) 
        except Exception as e: 
            return self._error(e) 

    def image_to_base64_data(self, src):
        try:
            with open(src, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(src)[1][1:].lower()
                if ext == 'jpg': ext = 'jpeg'
                return self._success(f"data:image/{ext};base64,{b64}")
        except Exception as e:
            return self._error(e)

    def image_convert(self, src, fmt, save_path=None):
        try:
            from PIL import Image
            target_fmt = fmt.upper()
            ext = "jpg" if target_fmt == "JPEG" else target_fmt.lower()
            if not save_path: save_path = self.save_file(f"converted.{ext}", [("Image", f"*.{ext}")])
            if not save_path: return self._error("Cancelled or failed")

            if target_fmt == "SVG":
                return self._save_as_svg(src, save_path)

            temp_src = src
            is_heic = src.lower().endswith((".heic", ".heif"))
            
            if is_heic:
                # 1. 尝试使用 pillow-heif (跨平台最佳方案)
                try:
                    try:
                        from pillow_heif import register_heif_opener
                        register_heif_opener()
                    except ImportError:
                        pass
                    with Image.open(src) as test_img:
                        test_img.verify()
                except Exception:
                    # 2. 如果没有安装库，尝试系统命令行工具
                    import platform
                    import subprocess
                    sys_name = platform.system()
                    temp_png = os.path.join(self.storage_dir, "temp_heic_conv.png")
                    
                    try:
                        if sys_name == "Darwin": # macOS
                            subprocess.run(["sips", "-s", "format", "png", src, "--out", temp_png], check=True, capture_output=True)
                            temp_src = temp_png
                        elif sys_name == "Linux": # Linux
                            # 通常由 libheif-examples 提供
                            subprocess.run(["heif-convert", src, temp_png], check=True, capture_output=True)
                            temp_src = temp_png
                        else:
                            raise Exception("Windows 或其他平台需安装 pillow-heif 库")
                    except Exception:
                        return self._error("当前环境无法直接处理 HEIC 格式。\n请运行 'pip install pillow-heif' 以获得跨平台支持。")

            with Image.open(temp_src) as img:
                actual_fmt = "JPEG" if target_fmt == "JPEG" else target_fmt
                if actual_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(save_path, actual_fmt)
            
            if temp_src != src and os.path.exists(temp_src):
                os.remove(temp_src)
                
            return self._success("Success")
        except Exception as e:
            return self._error(e)

    def _save_as_svg(self, src_path, save_path):
        """真正的矢量化转换：将像素区域转换为 SVG 路径"""
        try:
            from PIL import Image
            with Image.open(src_path) as img:
                # 如果图片太大，先进行适度缩放以防生成的 SVG 过大（超过 1000px 宽度则缩放）
                max_size = 800
                if img.width > max_size or img.height > max_size:
                    ratio = min(max_size / img.width, max_size / img.height)
                    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
                
                img = img.convert("RGBA")
                width, height = img.size
                pixels = img.load()

                # 颜色聚合：为了减少路径数量，对颜色进行微调（容差处理）
                def get_color_key(rgba):
                    if rgba[3] < 128: return None # 透明
                    # 将颜色稍微分组 (每 8 个色阶一组) 以减少生成的 path 数量
                    return "#%02x%02x%02x" % (rgba[0]//8*8, rgba[1]//8*8, rgba[2]//8*8)

                paths = {} # color -> list of rects (x, y, w)

                for y in range(height):
                    start_x = -1
                    last_color = None
                    for x in range(width):
                        color = get_color_key(pixels[x, y])
                        
                        if color != last_color:
                            if last_color is not None:
                                # 结束上一个色块
                                if last_color not in paths: paths[last_color] = []
                                paths[last_color].append((start_x, y, x - start_x))
                            
                            start_x = x
                            last_color = color
                    
                    # 处理每行最后一个色块
                    if last_color is not None:
                        if last_color not in paths: paths[last_color] = []
                        paths[last_color].append((start_x, y, width - start_x))

                # 生成 SVG 字符串
                svg_lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
                svg_lines.append('  <rect width="100%" height="100%" fill="none" />')
                
                for color, rects in paths.items():
                    path_data = []
                    for rx, ry, rw in rects:
                        # 使用 M (move to) 和 h (horizontal line) 构建路径，比绘制无数个 <rect> 效率高得多
                        path_data.append(f"M{rx} {ry}h{rw}")
                    
                    combined_path = "".join(path_data)
                    svg_lines.append(f'  <path d="{combined_path}" stroke="{color}" stroke-width="1.1" />')
                
                svg_lines.append('</svg>')
                
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(svg_lines))
                    
                return self._success("Success (True Vector)")
        except Exception as e:
            import traceback
            return self._error(f"矢量化失败: {str(e)}\n{traceback.format_exc()}")

    def image_compress(self, src, quality, save_path=None):
        try:
            from PIL import Image
            ext_orig = os.path.splitext(src)[1].lower()
            ext = "jpg" if ext_orig in [".jpg", ".jpeg"] else ext_orig.replace(".", "")
            if not save_path: save_path = self.save_file(f"compressed.{ext}", [("Image", f"*.{ext}")])
            if not save_path: return self._error("Cancelled or failed")
            with Image.open(src) as img:
                if "png" in ext.lower():
                    clevel = int((100 - int(quality)) / 10)
                    img.save(save_path, format="PNG", optimize=True, compress_level=clevel)
                else:
                    actual_fmt = "JPEG" if ext.lower() in ["jpg", "jpeg"] else "WEBP"
                    if actual_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(save_path, format=actual_fmt, quality=int(quality), optimize=True)
            return self._success("Success")
        except Exception as e:
            return self._error(e)

    def image_resize_crop(self, src, tw, th, mode, save_path=None):
        try:
            from PIL import Image
            ext = os.path.splitext(src)[1].lower().replace(".", "")
            if not save_path: save_path = self.save_file(f"processed.{ext}", [("Image", f"*.{ext}")])
            if not save_path: return self._error("Cancelled or failed")
            with Image.open(src) as img:
                w, h = img.size
                itw, ith = int(tw), int(th)
                if mode == "resize":
                    res = img.resize((itw, ith), Image.Resampling.LANCZOS)
                else:
                    if itw > w or ith > h: return self._error("Target size larger than original")
                    if mode == "center": left, top = (w-itw)//2, (h-ith)//2
                    elif mode == "tl": left, top = 0, 0
                    elif mode == "tr": left, top = w-itw, 0
                    elif mode == "bl": left, top = 0, h-ith
                    elif mode == "br": left, top = w-itw, h-ith
                    res = img.crop((left, top, left+itw, top+ith))
                res.save(save_path)
            return self._success("Success")
        except Exception as e:
            return self._error(e)

    def image_radius(self, src, radii, save_path=None):
        try:
            from PIL import Image, ImageDraw
            if not save_path: save_path = self.save_file("rounded.png", [("PNG", "*.png")])
            if not save_path: return self._error("Cancelled or failed")
            tl, tr, bl, br = [int(r) for r in radii]
            with Image.open(src) as img:
                img = img.convert("RGBA")
                w, h = img.size
                mask = Image.new("L", (w, h), 0)
                draw = ImageDraw.Draw(mask)
                x1, y1, x2, y2 = 0, 0, w, h
                if tl > 0: draw.pieslice([x1, y1, x1 + 2 * tl, y1 + 2 * tl], 180, 270, fill=255)
                if tr > 0: draw.pieslice([x2 - 2 * tr, y1, x2, y1 + 2 * tr], 270, 360, fill=255)
                if bl > 0: draw.pieslice([x1, y2 - 2 * bl, x1 + 2 * bl, y2], 90, 180, fill=255)
                if br > 0: draw.pieslice([x2 - 2 * br, y2 - 2 * br, x2, y2], 0, 90, fill=255)
                left, right, top, bottom = max(tl, bl), w - max(tr, br), max(tl, tr), h - max(bl, br)
                if left < right and top < bottom: draw.rectangle([left, top, right, bottom], fill=255)
                if tl > 0 or tr > 0: draw.rectangle([tl, 0, w - tr, top], fill=255)
                if bl > 0 or br > 0: draw.rectangle([bl, bottom, w - br, h], fill=255)
                if tl > 0 or bl > 0: draw.rectangle([0, tl, left, h - bl], fill=255)
                if tr > 0 or br > 0: draw.rectangle([right, tr, w, h - br], fill=255)
                img.putalpha(mask)
                img.save(save_path, "PNG")
            return self._success("Success")
        except Exception as e:
            return self._error(e)

    def image_to_base64_save(self, src):
        try:
            with open(src, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(src)[1][1:].lower()
                if ext == 'jpg': ext = 'jpeg'
                data = f"data:image/{ext};base64,{b64}"
            save_path = self.save_file("image_base64.txt", [("Text", "*.txt")]) 
            if not save_path: return self._error("Cancelled or failed")
            with open(save_path, "w") as f: 
                f.write(data) 
            return self._success("Success") 
        except Exception as e: 
            return self._error(e) 

    def save_image_from_base64(self, b64_data, filename="qrcode.png"): 
        try: 
            if "," in b64_data: b64_data = b64_data.split(",")[1] 
            img_data = base64.b64decode(b64_data) 
            save_path = self.save_file(filename, [("PNG files", "*.png")]) 
            if not save_path: return self._error("Cancelled or failed") 
            with open(save_path, "wb") as f: 
                f.write(img_data) 
            return self._success("Success") 
        except Exception as e: 
            return self._error(e) 

    def base64_to_image(self, b64_data):
        try:
            from PIL import Image
            from io import BytesIO
            if b64_data.startswith("data:image/"):
                try:
                    header, data = b64_data.split(",", 1)
                    mime = header.split(";")[0].split("/")[1]
                    img_format = mime.lower().replace("jpeg", "jpg")
                except:
                    return self._error("Base64 Data URI 格式错误")
            else:
                data = b64_data
                img_format = "png"
            
            try:
                img_data = base64.b64decode(data)
            except:
                return self._error("无效的 Base64 编码字符串")

            if not img_data:
                return self._error("解码后的数据为空")

            try:
                with Image.open(BytesIO(img_data)) as img:
                    img.verify()
            except:
                return self._error("Base64 数据内容不是有效的图片格式")

            save_path = self.save_file(f"restored.{img_format}", [("Image", f"*.{img_format}")])
            if not save_path: return self._error("Cancelled or failed")
            with open(save_path, "wb") as f:
                f.write(img_data)
            return self._success("Success")
        except Exception as e:
            return self._error(f"还原失败: {str(e)}")
    # ---- Terminal ----

    def term_create(self, tid):
        """创建终端会话"""
        try:
            from backend.terminal import TerminalSession
            tid = int(tid)
            session = TerminalSession()

            def _make_push(term_id):
                def _push(data):
                    import json as _json
                    encoded = _json.dumps(data)
                    js = f"if(window._termWrites&&window._termWrites[{term_id}])window._termWrites[{term_id}]({encoded})"
                    try:
                        self._window.evaluate_js(js)
                    except Exception:
                        pass
                return _push

            session.start(on_output=_make_push(tid))
            self._terms[tid] = session
            return self._success({"id": tid})
        except Exception as e:
            return self._error(str(e))

    def term_input(self, tid, data):
        """终端输入"""
        s = self._terms.get(int(tid))
        if s:
            s.write(data)
        return self._success(True)

    def term_resize(self, tid, cols, rows):
        """调整终端大小"""
        s = self._terms.get(int(tid))
        if s:
            s.resize(int(cols), int(rows))
        return self._success(True)

    def term_stop(self, tid):
        """停止终端"""
        s = self._terms.pop(int(tid), None)
        if s:
            s.stop()
        return self._success(True)

    def _get_translation_cache(self):
        path = os.path.join(self.storage_dir, "android_perms_zh_cache.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save_translation_cache(self, cache):
        path = os.path.join(self.storage_dir, "android_perms_zh_cache.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=4)
        except: pass

    def _translate_text(self, text, cache):
        if not text or text == '-' or len(text.strip()) == 0: return text
        if text in cache: return cache[text]
        
        try:
            # 使用 Google Translate GTX 免费接口
            import urllib.parse
            import urllib.request
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={urllib.parse.quote(text)}"
            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=context, timeout=5) as response:
                res = json.loads(response.read().decode('utf-8'))
                translated = "".join([part[0] for part in res[0]])
                cache[text] = translated
                return translated
        except Exception as e:
            self._log(f"Translation error: {e}")
            return text # 失败时返回原文

    def translate(self, text, source_lang, target_lang):
        """多语言翻译，使用 Google Translate GTX 免费接口"""
        try:
            import urllib.parse
            import urllib.request
            if not text or len(text.strip()) == 0:
                return self._error("请输入待翻译文本")
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                res = json.loads(response.read().decode('utf-8'))
                translated = "".join([part[0] for part in res[0]])
                # 如果返回了检测到的源语言
                detected = res[2] if len(res) > 2 and res[2] else source_lang
                return self._success({"translated": translated, "detected": detected})
        except Exception as e:
            return self._error(f"翻译失败: {str(e)}")

    def request_api(self, url, method, headers_json, body, ignore_ssl=False):
        try:
            import urllib.request
            import urllib.error
            import json
            
            
            headers = json.loads(headers_json) if headers_json else {}

            # 对 URL 中的非 ASCII 字符做百分号编码（保留已编码的 %XX 序列）
            try:
                parsed = urllib.parse.urlsplit(url)
                safe = "/:@?=&%#[]!$&'()*+,;=-._~"
                encoded_path = urllib.parse.quote(parsed.path, safe=safe)
                encoded_query = urllib.parse.quote(parsed.query, safe=safe)
                encoded_fragment = urllib.parse.quote(parsed.fragment, safe=safe) if parsed.fragment else ''
                url = urllib.parse.urlunsplit(
                    (parsed.scheme, parsed.netloc, encoded_path, encoded_query, encoded_fragment)
                )
            except Exception:
                pass  # URL 解析失败则使用原始 url

            # 智能处理 Body 编码
            if body:
                # 检查是否为表单格式
                is_form = False
                for k, v in headers.items():
                    if k.lower() == 'content-type' and 'application/x-www-form-urlencoded' in v.lower():
                        is_form = True
                        break
                
                if is_form:
                    # 对表单内容进行 URL 编码，保留结构字符 = 和 &
                    import urllib.parse
                    body = urllib.parse.quote_plus(body, safe='=&')
                
                data = body.encode('utf-8')
            else:
                data = None

            
            # 根据 ignore_ssl 参数决定是否忽略证书验证
            if ignore_ssl:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            else:
                ctx = ssl.create_default_context(cafile=certifi.where())
            
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            
            # 获取实际发送的请求头 (包含 urllib 自动补充的部分)
            actual_request_headers = {}
            lower_keys = set()
            for k, v in req.header_items():
                actual_request_headers[k] = v
                lower_keys.add(k.lower())
            
            # 模拟 urllib 底层自动补全的逻辑以便在 UI 显示 (忽略大小写进行判断)
            if 'user-agent' not in lower_keys:
                actual_request_headers['User-Agent'] = f"Python-urllib/{sys.version_info.major}.{sys.version_info.minor}"
            
            if 'host' not in lower_keys:
                from urllib.parse import urlparse
                actual_request_headers['Host'] = urlparse(url).netloc
            
            if data and 'content-length' not in lower_keys:
                actual_request_headers['Content-Length'] = str(len(data))
            
            if 'connection' not in lower_keys:
                actual_request_headers['Connection'] = 'close'

            try:
                # 设置 30 秒超时
                with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                    res_body = response.read().decode('utf-8', errors='replace')
                    res_headers = dict(response.info())
                    return self._success({
                        'status': response.status,
                        'headers': res_headers,
                        'body': res_body,
                        'request_headers': actual_request_headers
                    })
            except urllib.error.HTTPError as e:
                # 服务器返回了错误状态码 (如 400, 500)
                try:
                    err_body = e.read().decode('utf-8', errors='replace')
                except:
                    err_body = "无法读取错误响应体"
                return self._success({
                    'status': e.code,
                    'headers': dict(e.headers),
                    'body': err_body,
                    'request_headers': actual_request_headers
                })
            except urllib.error.URLError as e:
                return self._error(f'请求失败: {str(e.reason)}')
            except Exception as e:
                return self._error(f'请求异常: {str(e)}')
        except Exception as e:
            return self._error(f'后端逻辑错误: {str(e)}')
