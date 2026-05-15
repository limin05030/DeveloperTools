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

    def _success(self, data):
        return {"success": True, "data": data}

    def _error(self, message):
        return {"success": False, "error": str(message)}

    def select_file(self):
        try:
            self._log("Opening select_file dialog...")
            result = self._window.create_file_dialog(webview.OPEN_DIALOG)
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
            elif fmt_type == "html_xml":
                is_xml = data.startswith("<?xml") or ("<" in data and not data.lower().startswith("<!doctype html"))
                soup = BeautifulSoup(data, "xml" if is_xml else "html.parser")
                res = soup.prettify()
            elif fmt_type == "js_format":
                res = self._js_format(data)
            elif fmt_type == "js_compress":
                res = self._js_compress(data)
            else: return self._error("Unknown format type")
            return self._success(res)
        except Exception as e:
            return self._error(e)

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

    def image_convert(self, src, fmt):
        try:
            ext = "jpg" if fmt.upper() == "JPEG" else fmt.lower()
            save_path = self.save_file(f"converted.{ext}", [("Image", f"*.{ext}")])
            if not save_path: return self._error("Cancelled or failed")
            with Image.open(src) as img:
                actual_fmt = "JPEG" if fmt.upper() == "JPEG" else fmt.upper()
                if actual_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(save_path, actual_fmt)
            return self._success("Success")
        except Exception as e:
            return self._error(e)

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
