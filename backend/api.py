# -*- coding: utf-8 -*-
import ssl
import sys
import webbrowser
import urllib.request
import os
import re
import json
import hashlib
import hmac
import base64
import urllib.parse
import html
import time
import uuid

import certifi
import qrcode
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image, ImageDraw
import zhconv
from bs4 import BeautifulSoup, formatter
import webview

class Api:
    def __init__(self, is_debug: bool=False):
        self._window = None
        self._debug = is_debug
        self._raw_uuids = []
        self.APPLE_OFFSET = 978307200
        self.storage_dir = os.path.join(os.path.expanduser("~"), ".developer_tools")
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass

    def set_window(self, window):
        self._window = window
    def open_url(self, url):
        try:
            webbrowser.open(url)
            return self._success(True)
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

    # --- Encode Tools ---
    def encode_decode(self, data, action):
        try:
            if action == "b64_encode": res = base64.b64encode(data.encode()).decode()
            elif action == "b64_decode": res = base64.b64decode(data.encode()).decode()
            elif action == "url_encode": res = urllib.parse.quote(data, safe='/:?=&')
            elif action == "url_decode": res = urllib.parse.unquote(data)
            elif action == "utf8_encode": res = "".join([f"\\x{b:02x}" for b in data.encode('utf-8')])
            elif action == "utf8_decode": res = bytes.fromhex(data.replace("\\x", "")).decode('utf-8')
            elif action == "unicode_encode": res = data.encode('unicode_escape').decode('ascii')
            elif action == "unicode_decode": res = data.encode().decode('unicode_escape')
            elif action == "html_escape": res = html.escape(data)
            elif action == "html_unescape": res = html.unescape(data)
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

    def _css_format(self, data):
        # 简单实现：每个规则换行，大括号缩进
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
        return '\n'.join(formatted).strip()

    def _css_compress(self, data):
        # 移除注释
        data = re.sub(r'/\*.*?\*/', '', data, flags=re.DOTALL)
        # 移除换行和多余空格
        data = re.sub(r'\s+', ' ', data)
        # 移除符号周围的空格
        data = re.sub(r'\s*([{:;,])\s*', r'\1', data)
        return data.strip()

    def _js_format(self, code):
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
        return '\n'.join(formatted)

    def _js_compress(self, code):
        # 移除单行注释
        code = re.sub(r'//.*', '', code)
        # 移除多行注释
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # 移除换行和连续空格
        code = re.sub(r'\s+', ' ', code)
        # 移除操作符周围的空格 (优化)
        code = re.sub(r'\s*([{}()\[\]=+\-*/%&|^<>!?:;,])\s*', r'\1', code)
        return code.strip()

    def _lua_compress(self, code):
        # 1. 移除多行注释 --[[ ]]
        code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
        # 2. 移除单行注释 --
        code = re.sub(r'--.*', '', code)
        # 3. 压缩空白
        code = re.sub(r'\s+', ' ', code)
        # 4. 移除操作符周围空格
        code = re.sub(r'\s*([{}()\[\]=+\-*/%#^<>~:;,])\s*', r'\1', code)
        return code.strip()

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
            return self._error(f"转换失败: 请检查输入数值是否符合 {from_base} 进制规则")

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
            with Image.open(src) as img: 
                return self._success({"width": img.width, "height": img.height}) 
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

    def image_convert(self, src, fmt):
        try:
            target_fmt = fmt.upper()
            ext = "jpg" if target_fmt == "JPEG" else target_fmt.lower()
            save_path = self.save_file(f"converted.{ext}", [("Image", f"*.{ext}")])
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

    def image_compress(self, src, quality):
        try:
            ext_orig = os.path.splitext(src)[1].lower()
            ext = "jpg" if ext_orig in [".jpg", ".jpeg"] else ext_orig.replace(".", "")
            save_path = self.save_file(f"compressed.{ext}", [("Image", f"*.{ext}")])
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

    def image_resize_crop(self, src, tw, th, mode):
        try:
            ext = os.path.splitext(src)[1].lower().replace(".", "")
            save_path = self.save_file(f"processed.{ext}", [("Image", f"*.{ext}")])
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

    def image_radius(self, src, radii):
        try:
            save_path = self.save_file("rounded.png", [("PNG", "*.png")])
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
                ext = os.path.splitext(src)[1][1:] 
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
            if b64_data.startswith("data:image/"):
                header, data = b64_data.split(",", 1)
                mime = header.split(";")[0].split("/")[1]
                img_format = mime.lower().replace("jpeg", "jpg")
            else:
                data = b64_data
                img_format = "png"
            img_data = base64.b64decode(data)
            save_path = self.save_file(f"restored.{img_format}", [("Image", f"*.{img_format}")])
            if not save_path: return self._error("Cancelled or failed")
            with open(save_path, "wb") as f:
                f.write(img_data)
            return self._success("Success")
        except Exception as e:
            return self._error(e)
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

    def request_api(self, url, method, headers_json, body, ignore_ssl=False):
        try:
            import urllib.request
            import urllib.error
            import json
            
            
            headers = json.loads(headers_json) if headers_json else {}
            
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
                    body = urllib.parse.quote(body, safe='=&')
                
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
