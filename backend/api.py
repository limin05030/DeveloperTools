# -*- coding: utf-8 -*-
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
import qrcode
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image, ImageDraw
import zhconv
from bs4 import BeautifulSoup
import webview

class Api:
    def __init__(self, isDebug: bool = False):
        self._window = None
        self._debug = isDebug
        self._raw_uuids = []
        self.APPLE_OFFSET = 978307200

    def set_window(self, window):
        self._window = window

    def _log(self, msg):
        if self._debug:
            print(f"[Backend API] {msg}")

    def select_file(self):
        try:
            self._log("Opening select_file dialog...")
            result = self._window.create_file_dialog(webview.OPEN_DIALOG)
            if result and isinstance(result, (list, tuple)):
                return result[0]
            return result
        except Exception as e:
            self._log(f"Error in select_file: {str(e)}")
            return f"Error: {str(e)}"

    def save_file(self, filename, patterns):
        """
        macOS 下 pywebview 对过滤器非常敏感。
        如果 patterns 报错，我们将尝试更简单的格式。
        """
        # 尝试几种不同的格式
        formats_to_try = []
        
        # 格式 1: 官方推荐的带通配符的交替元组
        ft1 = []
        for desc, pat in patterns:
            ft1.append(desc)
            ft1.append(pat)
        formats_to_try.append(tuple(ft1))
        
        # 格式 2: 纯后缀格式 (针对 macOS Cocoa)
        ft2 = []
        for desc, pat in patterns:
            ext = pat.split('.')[-1]
            ft2.append(desc)
            ft2.append(ext)
        formats_to_try.append(tuple(ft2))
        
        # 格式 3: 无过滤器
        formats_to_try.append(None)

        last_error = None
        for ft in formats_to_try:
            try:
                self._log(f"Attempting create_file_dialog with ft={ft}")
                result = self._window.create_file_dialog(
                    webview.SAVE_DIALOG, 
                    save_filename=filename, 
                    file_types=ft if ft else ()
                )
                self._log(f"Dialog success with ft={ft}")
                if result and isinstance(result, (list, tuple)):
                    return result[0]
                return result
            except Exception as e:
                last_error = str(e)
                self._log(f"Format {ft} failed: {last_error}")
                continue
        
        return f"Error: {last_error}"

    # --- Hash Tools ---
    def calc_hash(self, data, algo, is_hmac, key_str):
        try:
            key = key_str.encode()
            actual_algo = "md5" if algo.startswith("md5") else algo
            h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
            h.update(data.encode('utf-8'))
            res = h.hexdigest()
            return res[8:24] if algo == "md5-16" else res
        except Exception as e:
            return f"Error: {str(e)}"

    def calc_file_hash(self, path, algo, is_hmac, key_str):
        try:
            if not os.path.isfile(path): return "Error: File not found"
            key = key_str.encode()
            actual_algo = "md5" if algo.startswith("md5") else algo
            h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            res = h.hexdigest()
            return res[8:24] if algo == "md5-16" else res
        except Exception as e:
            return f"Error: {str(e)}"

    # --- Encode Tools ---
    def encode_decode(self, data, action):
        try:
            if action == "b64_encode": return base64.b64encode(data.encode()).decode()
            if action == "b64_decode": return base64.b64decode(data.encode()).decode()
            if action == "url_encode": return urllib.parse.quote(data, safe='/:?=&')
            if action == "url_decode": return urllib.parse.unquote(data)
            if action == "utf8_encode": return "".join([f"\\x{b:02x}" for b in data.encode('utf-8')])
            if action == "utf8_decode": return bytes.fromhex(data.replace("\\x", "")).decode('utf-8')
            if action == "unicode_encode": return data.encode('unicode_escape').decode('ascii')
            if action == "unicode_decode": return data.encode().decode('unicode_escape')
            if action == "html_escape": return html.escape(data)
            if action == "html_unescape": return html.unescape(data)
            if action == "upper": return data.upper()
            if action == "lower": return data.lower()
            if action == "swap": return data.swapcase()
            if action == "traditional": return zhconv.convert(data, 'zh-hant')
            if action == "simplified": return zhconv.convert(data, 'zh-hans')
            return "Unknown action"
        except Exception as e:
            return f"Error: {str(e)}"

    # --- Format Tools ---
    def format_data(self, data, fmt_type):
        try:
            if fmt_type == "json_format":
                return json.dumps(json.loads(data), indent=4, ensure_ascii=False)
            if fmt_type == "json_compress":
                return json.dumps(json.loads(data), separators=(',', ':'), ensure_ascii=False)
            if fmt_type == "html_xml":
                is_xml = data.startswith("<?xml") or ("<" in data and not data.lower().startswith("<!doctype html"))
                soup = BeautifulSoup(data, "xml" if is_xml else "html.parser")
                return soup.prettify()
            if fmt_type == "js_format":
                return self._js_format(data)
            if fmt_type == "js_compress":
                return self._js_compress(data)
            return "Unknown format type"
        except Exception as e:
            return f"Error: {str(e)}"

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
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'\s+', ' ', code)
        return code.strip()

    # --- Time Tools ---
    def get_current_time(self, tz_offset):
        now = time.time()
        tz = timezone(timedelta(hours=tz_offset))
        dt_str = datetime.fromtimestamp(now, tz=tz).strftime("%Y-%m-%d %H:%M:%S.%f")
        return {"ts": int(now * 1000), "date": dt_str[:-3]}

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
            return res[:-3] if show_ms else res
        except Exception as e:
            return f"Error: {str(e)}"

    def date_to_ts(self, date_str, tz_offset, is_ios):
        try:
            fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in date_str else "%Y-%m-%d %H:%M:%S"
            dt = datetime.strptime(date_str, fmt)
            tz = timezone(timedelta(hours=tz_offset))
            unix_ts = dt.replace(tzinfo=tz).timestamp()
            if is_ios:
                unix_ts -= self.APPLE_OFFSET
                return f"{unix_ts:.3f}".rstrip('0').rstrip('.')
            else:
                return str(int(unix_ts * 1000)) if "." in date_str else str(int(unix_ts))
        except Exception as e:
            return f"Error: {str(e)}"

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
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_uuids(self, count, hyphen, upper, braces):
        self._raw_uuids = [str(uuid.uuid4()) for _ in range(int(count))]
        results = []
        for u in self._raw_uuids:
            processed = u
            if not hyphen: processed = processed.replace("-", "")
            if upper: processed = processed.upper()
            if braces: processed = "{" + processed + "}"
            results.append(processed)
        return "\n".join(results)

    # --- Image Tools ---
    def get_image_info(self, src): 
        try: 
            with Image.open(src) as img: 
                return {"width": img.width, "height": img.height} 
        except Exception as e: 
            return {"error": str(e)} 

    def read_text_file(self): 
        path = self.select_file() 
        if not path or path.startswith("Error"): return path 
        try: 
            with open(path, "r", encoding="utf-8") as f: 
                return f.read() 
        except Exception as e: 
            return f"Error: {str(e)}" 

    def image_convert(self, src, fmt):
        try:
            if src.lower().endswith(fmt.lower()):
                return ""

            self._log(f"image_convert: src={src}, fmt={fmt}")
            ext = "jpg" if fmt.upper() == "JPEG" else fmt.lower()
            save_path = self.save_file(f"converted.{ext}", [("Image", f"*.{ext}")])
            if not save_path or save_path == "Cancelled" or save_path.startswith("Error:"):
                return save_path
            with Image.open(src) as img:
                actual_fmt = "JPEG" if fmt.upper() == "JPEG" else fmt.upper()
                if actual_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(save_path, actual_fmt)
            return "Success"
        except Exception as e:
            self._log(f"Error in image_convert: {str(e)}")
            return f"Error: {str(e)}"

    def image_compress(self, src, quality):
        try:
            self._log(f"image_compress: src={src}, quality={quality}")
            ext_orig = os.path.splitext(src)[1].lower()
            ext = "jpg" if ext_orig in [".jpg", ".jpeg"] else ext_orig.replace(".", "")
            save_path = self.save_file(f"compressed.{ext}", [("Image", f"*.{ext}")])
            if not save_path or save_path == "Cancelled" or save_path.startswith("Error:"):
                return save_path
            with Image.open(src) as img:
                if "png" in ext.lower():
                    clevel = int((100 - int(quality)) / 10)
                    img.save(save_path, format="PNG", optimize=True, compress_level=clevel)
                else:
                    actual_fmt = "JPEG" if ext.lower() in ["jpg", "jpeg"] else "WEBP"
                    if actual_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(save_path, format=actual_fmt, quality=int(quality), optimize=True)
            return "Success"
        except Exception as e:
            self._log(f"Error in image_compress: {str(e)}")
            return f"Error: {str(e)}"

    def image_resize_crop(self, src, tw, th, mode):
        try:
            self._log(f"image_resize_crop: src={src}, tw={tw}, th={th}, mode={mode}")
            ext = os.path.splitext(src)[1].lower().replace(".", "")
            save_path = self.save_file(f"processed.{ext}", [("Image", f"*.{ext}")])
            if not save_path or save_path == "Cancelled" or save_path.startswith("Error:"):
                return save_path
            with Image.open(src) as img:
                w, h = img.size
                itw, ith = int(tw), int(th)
                if mode == "resize":
                    res = img.resize((itw, ith), Image.Resampling.LANCZOS)
                else:
                    if itw > w or ith > h:
                        return f"Error: Target size {itw}x{ith} larger than original {w}x{h}"
                    if mode == "center": left, top = (w-itw)//2, (h-ith)//2
                    elif mode == "tl": left, top = 0, 0
                    elif mode == "tr": left, top = w-itw, 0
                    elif mode == "bl": left, top = 0, h-ith
                    elif mode == "br": left, top = w-itw, h-ith
                    res = img.crop((left, top, left+itw, top+ith))
                res.save(save_path)
            return "Success"
        except Exception as e:
            self._log(f"Error in image_resize_crop: {str(e)}")
            return f"Error: {str(e)}"

    def image_radius(self, src, radii):
        try:
            self._log(f"image_radius: src={src}, radii={radii}")
            save_path = self.save_file("rounded.png", [("PNG", "*.png")])
            if not save_path or save_path == "Cancelled" or save_path.startswith("Error:"):
                return save_path
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
            return "Success"
        except Exception as e:
            self._log(f"Error in image_radius: {str(e)}")
            return f"Error: {str(e)}"

    def image_to_base64_save(self, src): 
        try: 
            self._log(f"image_to_base64_save: src={src}")
            with open(src, "rb") as f: 
                b64 = base64.b64encode(f.read()).decode() 
                ext = os.path.splitext(src)[1][1:] 
                data = f"data:image/{ext};base64,{b64}" 
            save_path = self.save_file("image_base64.txt", [("Text", "*.txt")]) 
            if not save_path or save_path == "Cancelled" or save_path.startswith("Error:"):
                return save_path
            with open(save_path, "w") as f: 
                f.write(data) 
            return "Success" 
        except Exception as e: 
            self._log(f"Error in image_to_base64_save: {str(e)}")
            return f"Error: {str(e)}" 

    def save_image_from_base64(self, b64_data, filename="qrcode.png"): 
        try: 
            if "," in b64_data: 
                b64_data = b64_data.split(",")[1] 
            img_data = base64.b64decode(b64_data) 
            save_path = self.save_file(filename, [("PNG files", "*.png"), ("All files", "*.*")]) 
            if not save_path or save_path == "Cancelled" or save_path.startswith("Error:"): 
                return save_path 
            with open(save_path, "wb") as f: 
                f.write(img_data) 
            return "Success" 
        except Exception as e: 
            return f"Error: {str(e)}" 

    def base64_to_image(self, b64_data):
        try:
            self._log("base64_to_image starting...")
            if b64_data.startswith("data:image/"):
                header, data = b64_data.split(",", 1)
                mime = header.split(";")[0].split("/")[1]
                img_format = mime.lower().replace("jpeg", "jpg")
            else:
                data = b64_data
                img_format = "png"
            img_data = base64.b64decode(data)
            save_path = self.save_file(f"restored.{img_format}", [("Image", f"*.{img_format}")])
            if not save_path or save_path == "Cancelled" or save_path.startswith("Error:"):
                return save_path
            with open(save_path, "wb") as f:
                f.write(img_data)
            return "Success"
        except Exception as e:
            self._log(f"Error in base64_to_image: {str(e)}")
            return f"Error: {str(e)}"
