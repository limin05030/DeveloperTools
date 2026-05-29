/* @ts-self-types="./lua_fmt.d.ts" */

import * as wasm from "./lua_fmt_bg.wasm";
import { __wbg_set_wasm } from "./lua_fmt_bg.js";
__wbg_set_wasm(wasm);

export {
    format, format_range
} from "./lua_fmt_bg.js";
