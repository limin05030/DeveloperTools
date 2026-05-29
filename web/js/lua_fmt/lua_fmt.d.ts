/**
 * WASM formatter for Lua using StyLua.
 *
 * @example
 * ```ts
 * import { format } from "@wasm-fmt/lua_fmt";
 *
 * const input = "function foo()\nreturn 42\nend";
 * const output = format(input);
 * ```
 *
 * @module
 */

/* tslint:disable */
/* eslint-disable */

import type { Config, Range } from "./lua_fmt_config.d.ts";
export type * from "./lua_fmt_config.d.ts";



/**
 * Formats the given Lua code according to the provided configuration.
 * @param input - Lua code to format
 * @param config - Configuration for formatting
 */
export function format(input: string, config?: Config | null): string;

/**
 * Formats a specific range of Lua code.
 * @param input - Lua code to format
 * @param range - Byte offset range
 * @param config - Configuration for formatting
 */
export function format_range(input: string, range: Range, config?: Config | null): string;
