// runtime/typesht-runtime.ts
// Python behavior runtime for TypeSht
// Imported as: import * as $ from "typesht-runtime";

import * as _nodePath from "node:path";
import * as _nodeFs   from "node:fs";

// ---------------------------------------------------------------------------
// 1. print()
// ---------------------------------------------------------------------------

export function print(...args: any[]): void {
    // Last argument may be an options object: { sep?: string, end?: string }
    let sep   = " ";
    let end   = "\n";
    let parts = [...args];

    const last = parts[parts.length - 1];
    if (last !== null && typeof last === "object" && !Array.isArray(last) &&
        ("sep" in last || "end" in last)) {
        const opts = parts.pop();
        if (opts.sep !== undefined) sep = opts.sep;
        if (opts.end !== undefined) end = opts.end;
    }

    const out = parts.map(pyStr).join(sep);

    if (typeof process !== "undefined" && process.stdout &&
        typeof process.stdout.write === "function") {
        // Node.js — supports custom end and no-newline printing
        process.stdout.write(out + end);
    } else {
        // Browser / non-Node fallback — console.log always adds a newline,
        // so we can only approximate: strip trailing newline if end === "\n"
        if (end === "\n") {
            console.log(out);
        } else {
            console.log(out + end);
        }
    }
}


// ---------------------------------------------------------------------------
// 2. String operations
// ---------------------------------------------------------------------------

export function str_index(s: string, i: number): string {
    const idx = i < 0 ? s.length + i : i;
    if (idx < 0 || idx >= s.length) {
        throw new IndexError(`string index out of range`);
    }
    return s[idx];
}

export function str_slice(s: string, start: number | null, stop: number | null, step: number | null): string {
    return _slice(s.split(""), start, stop, step).join("");
}

export function str_mul(s: string, n: number): string {
    if (n <= 0) return "";
    return s.repeat(n);
}

export function contains(container: any, item: any): boolean {
    if (typeof container === "string") {
        return container.includes(String(item));
    }
    if (Array.isArray(container)) {
        return container.some(el => pyEq(el, item));
    }
    if (container instanceof PyDict) {
        return container.has(item);
    }
    throw new TypeError(`argument of type '${pyType(container)}' is not iterable`);
}


// ---------------------------------------------------------------------------
// 3. List operations
// ---------------------------------------------------------------------------

export function index(obj: any, i: number): any {
    if (typeof obj === "string") return str_index(obj, i);
    if (Array.isArray(obj)) {
        const idx = i < 0 ? obj.length + i : i;
        if (idx < 0 || idx >= obj.length) {
            throw new IndexError(`list index out of range`);
        }
        return obj[idx];
    }
    throw new TypeError(`'${pyType(obj)}' object is not subscriptable`);
}

export function slice(obj: any, start: number | null, stop: number | null, step: number | null): any {
    if (typeof obj === "string") return str_slice(obj, start, stop, step);
    if (Array.isArray(obj))     return _slice(obj, start, stop, step);
    throw new TypeError(`'${pyType(obj)}' object is not subscriptable`);
}

function _slice<T>(arr: T[], start: number | null, stop: number | null, step: number | null): T[] {
    const n    = arr.length;
    const st   = step ?? 1;
    if (st === 0) throw new ValueError("slice step cannot be zero");

    let lo: number, hi: number;
    if (st > 0) {
        lo = start === null ? 0      : start < 0 ? Math.max(0, n + start)  : Math.min(start, n);
        hi = stop  === null ? n      : stop  < 0 ? Math.max(0, n + stop)   : Math.min(stop,  n);
    } else {
        lo = start === null ? n - 1  : start < 0 ? Math.max(-1, n + start) : Math.min(start, n - 1);
        hi = stop  === null ? -(n+1) : stop  < 0 ? Math.max(-1, n + stop)  : Math.min(stop,  n - 1);
    }

    const result: T[] = [];
    if (st > 0) {
        for (let i = lo; i < hi; i += st) result.push(arr[i]);
    } else {
        for (let i = lo; i > hi; i += st) result.push(arr[i]);
    }
    return result;
}


// ---------------------------------------------------------------------------
// 4. PyDict — Python dict with ordered keys and Python iteration behavior
// ---------------------------------------------------------------------------

export class PyDict {
    private _keys:   any[] = [];
    private _values: any[] = [];

    constructor(pairs: [any, any][] = []) {
        for (const [k, v] of pairs) {
            this.set(k, v);
        }
    }

    private _find(key: any): number {
        return this._keys.findIndex(k => pyEq(k, key));
    }

    set(key: any, value: any): void {
        const i = this._find(key);
        if (i >= 0) {
            this._values[i] = value;
        } else {
            this._keys.push(key);
            this._values.push(value);
        }
    }

    get(key: any, defaultVal: any = null): any {
        const i = this._find(key);
        if (i < 0) return defaultVal;
        return this._values[i];
    }

    has(key: any): boolean {
        return this._find(key) >= 0;
    }

    delete(key: any): void {
        const i = this._find(key);
        if (i < 0) throw new KeyError(String(key));
        this._keys.splice(i, 1);
        this._values.splice(i, 1);
    }

    [Symbol.iterator](): Iterator<any> {
        return this._keys[Symbol.iterator]();
    }

    keys():   Iterable<any> { return this._keys[Symbol.iterator]()   as any; }
    values(): Iterable<any> { return this._values[Symbol.iterator]() as any; }
    items():  Iterable<[any, any]> {
        const pairs: [any, any][] = this._keys.map((k, i) => [k, this._values[i]]);
        return pairs[Symbol.iterator]() as any;
    }

    get size(): number { return this._keys.length; }

    toString(): string {
        const pairs = this._keys.map((k, i) =>
            `${pyRepr(k)}: ${pyRepr(this._values[i])}`
        );
        return `{${pairs.join(", ")}}`;
    }
}

export function dict(pairs: [any, any][]): PyDict {
    return new PyDict(pairs);
}


// ---------------------------------------------------------------------------
// 5. Math helpers
// ---------------------------------------------------------------------------

export function floordiv(a: number, b: number): number {
    if (b === 0) throw new ZeroDivisionError("integer division or modulo by zero");
    return Math.floor(a / b);
}

export function pymod(a: number, b: number): number {
    if (b === 0) throw new ZeroDivisionError("integer division or modulo by zero");
    return ((a % b) + b) % b;
}


// ---------------------------------------------------------------------------
// 6. Built-in functions
// ---------------------------------------------------------------------------

export function len(x: any): number {
    if (typeof x === "string")    return x.length;
    if (Array.isArray(x))         return x.length;
    if (x instanceof PyDict)      return x.size;
    throw new TypeError(`object of type '${pyType(x)}' has no len()`);
}

export function range(startOrStop: number, stop?: number, step?: number): number[] {
    let start: number, end: number, st: number;
    if (stop === undefined) {
        start = 0; end = startOrStop; st = 1;
    } else {
        start = startOrStop; end = stop; st = step ?? 1;
    }
    if (st === 0) throw new ValueError("range() arg 3 must not be zero");
    const result: number[] = [];
    if (st > 0) {
        for (let i = start; i < end; i += st) result.push(i);
    } else {
        for (let i = start; i > end; i += st) result.push(i);
    }
    return result;
}

export function type(x: any): string {
    if (x === null)              return "NoneType";
    if (typeof x === "boolean")  return "bool";
    if (typeof x === "number")   return Number.isInteger(x) ? "int" : "float";
    if (typeof x === "string")   return "str";
    if (Array.isArray(x))        return "list";
    if (x instanceof PyDict)     return "dict";
    return x?.constructor?.name ?? "object";
}

export function isinstance(x: any, t: string): boolean {
    return type(x) === t;
}

export function int(x: any): number {
    if (typeof x === "number")  return Math.trunc(x);
    if (typeof x === "boolean") return x ? 1 : 0;
    if (typeof x === "string") {
        const n = Number(x.trim());
        if (isNaN(n)) throw new ValueError(`invalid literal for int(): '${x}'`);
        return Math.trunc(n);
    }
    throw new TypeError(`int() argument must be a string or number`);
}

export function float(x: any): number {
    if (typeof x === "number")  return x;
    if (typeof x === "boolean") return x ? 1.0 : 0.0;
    if (typeof x === "string") {
        const n = Number(x.trim());
        if (isNaN(n)) throw new ValueError(`could not convert string to float: '${x}'`);
        return n;
    }
    throw new TypeError(`float() argument must be a string or number`);
}

export function str(x: any): string {
    return pyStr(x);
}

export function abs(x: number): number {
    return Math.abs(x);
}

export function max(...args: any[]): any {
    const items = args.length === 1 && Array.isArray(args[0]) ? args[0] : args;
    if (items.length === 0) throw new ValueError("max() arg is an empty sequence");
    return items.reduce((a: any, b: any) => (b > a ? b : a));
}

export function min(...args: any[]): any {
    const items = args.length === 1 && Array.isArray(args[0]) ? args[0] : args;
    if (items.length === 0) throw new ValueError("min() arg is an empty sequence");
    return items.reduce((a: any, b: any) => (b < a ? b : a));
}

export function sum(items: number[], start: number = 0): number {
    return items.reduce((acc, x) => acc + x, start);
}

export function zip(...iterables: any[][]): any[][] {
    const minLen = Math.min(...iterables.map(it => it.length));
    return Array.from({ length: minLen }, (_, i) => iterables.map(it => it[i]));
}

export function enumerate(iterable: any[], start: number = 0): [number, any][] {
    return iterable.map((item, i) => [i + start, item]);
}

export function map(fn: (x: any) => any, iterable: any[]): any[] {
    return iterable.map(fn);
}

export function filter(fn: (x: any) => boolean, iterable: any[]): any[] {
    return iterable.filter(fn);
}

export function sorted(iterable: any[], reverse: boolean = false): any[] {
    const copy = [...iterable];
    copy.sort((a, b) => pyCompare(a, b));
    if (reverse) copy.reverse();
    return copy;
}

export function reversed(iterable: any[]): any[] {
    return [...iterable].reverse();
}


// ---------------------------------------------------------------------------
// 7. Python-style errors
// ---------------------------------------------------------------------------

export class ValueError extends Error {
    constructor(msg: string) { super(msg); this.name = "ValueError"; }
}

export class TypeError extends Error {
    constructor(msg: string) { super(msg); this.name = "TypeError"; }
}

export class IndexError extends Error {
    constructor(msg: string) { super(msg); this.name = "IndexError"; }
}

export class KeyError extends Error {
    constructor(msg: string) { super(msg); this.name = "KeyError"; }
}

export class ZeroDivisionError extends Error {
    constructor(msg: string) { super(msg); this.name = "ZeroDivisionError"; }
}

export class RuntimeError extends Error {
    constructor(msg: string) { super(msg); this.name = "RuntimeError"; }
}


// ---------------------------------------------------------------------------
// 8. Standard library module bindings
// ---------------------------------------------------------------------------

// --- math ---
export const math = {
    pi:     Math.PI,
    e:      Math.E,
    sqrt:   Math.sqrt,
    floor:  Math.floor,
    ceil:   Math.ceil,
    abs:    Math.abs,
    pow:    Math.pow,
    log:    Math.log,
    log2:   Math.log2,
    log10:  Math.log10,
    sin:    Math.sin,
    cos:    Math.cos,
    tan:    Math.tan,
    asin:   Math.asin,
    acos:   Math.acos,
    atan:   Math.atan,
    atan2:  Math.atan2,
    exp:    Math.exp,
    trunc:  Math.trunc,
    inf:    Infinity,
    nan:    NaN,
    isnan:  (x: number) => isNaN(x),
    isinf:  (x: number) => !isFinite(x) && !isNaN(x),
    gcd:    (a: number, b: number): number => {
        a = Math.abs(a); b = Math.abs(b);
        while (b) { [a, b] = [b, a % b]; }
        return a;
    },
    factorial: (n: number): number => {
        if (n < 0) throw new ValueError("math domain error");
        if (n === 0) return 1;
        let result = 1;
        for (let i = 2; i <= n; i++) result *= i;
        return result;
    },
};

// --- random ---
export const random = {
    random:  (): number => Math.random(),
    randint: (a: number, b: number): number => Math.floor(Math.random() * (b - a + 1)) + a,
    uniform: (a: number, b: number): number => Math.random() * (b - a) + a,
    choice:  (seq: any[]): any => seq[Math.floor(Math.random() * seq.length)],
    shuffle: (seq: any[]): void => {
        for (let i = seq.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [seq[i], seq[j]] = [seq[j], seq[i]];
        }
    },
    sample: (seq: any[], k: number): any[] => {
        const copy = [...seq];
        random.shuffle(copy);
        return copy.slice(0, k);
    },
    seed: (_s: any): void => {
        // JavaScript has no seedable RNG — no-op for API compatibility
    },
};

// --- json ---
function _toJsonSafe(obj: any): any {
    if (obj instanceof PyDict) {
        const result: any = {};
        for (const [k, v] of obj.items()) {
            result[String(k)] = _toJsonSafe(v);
        }
        return result;
    }
    if (Array.isArray(obj)) return obj.map(_toJsonSafe);
    return obj;
}

export const json = {
    dumps: (obj: any, indent?: number): string => {
        const safe = _toJsonSafe(obj);
        return indent !== undefined
            ? JSON.stringify(safe, null, indent)
            : JSON.stringify(safe);
    },
    loads: (s: string): any => {
        try {
            return JSON.parse(s);
        } catch {
            throw new ValueError(`JSON decode error: invalid JSON`);
        }
    },
};

// --- re ---
export const re = {
    match: (pattern: string, s: string, flags: string = "") => {
        const r = new RegExp("^" + pattern, flags);
        const m = s.match(r);
        return m ? { group: (i: number = 0) => m[i], groups: () => m.slice(1) } : null;
    },
    search: (pattern: string, s: string, flags: string = "") => {
        const r = new RegExp(pattern, flags);
        const m = s.match(r);
        return m ? { group: (i: number = 0) => m[i], groups: () => m.slice(1) } : null;
    },
    findall: (pattern: string, s: string, flags: string = ""): string[] => {
        const r = new RegExp(pattern, "g" + flags);
        return s.match(r) ?? [];
    },
    sub: (pattern: string, repl: string, s: string, flags: string = ""): string => {
        const r = new RegExp(pattern, "g" + flags);
        return s.replace(r, repl);
    },
    split: (pattern: string, s: string, flags: string = ""): string[] => {
        const r = new RegExp(pattern, flags);
        return s.split(r);
    },
    compile: (pattern: string, flags: string = "") => ({
        match:   (s: string) => re.match(pattern, s, flags),
        search:  (s: string) => re.search(pattern, s, flags),
        findall: (s: string) => re.findall(pattern, s, flags),
        sub:     (repl: string, s: string) => re.sub(pattern, repl, s, flags),
        split:   (s: string) => re.split(pattern, s, flags),
    }),
};

// --- sys ---
export const sys = {
    get argv(): string[] {
        if (typeof process !== "undefined") return process.argv.slice(1);
        return [];
    },
    exit: (code: number = 0): void => {
        if (typeof process !== "undefined") process.exit(code);
        throw new RuntimeError(`sys.exit(${code})`);
    },
    get version(): string { return "TypeSht/1.0"; },
    get platform(): string {
        if (typeof process !== "undefined") return process.platform;
        return "browser";
    },
};

// --- os (path operations only — Node.js only) ---
export const os = {
    path: {
        join:     (...args: string[]): string => _nodePath.join(...args),
        dirname:  (p: string): string => _nodePath.dirname(p),
        basename: (p: string, ext?: string): string => _nodePath.basename(p, ext),
        abspath:  (p: string): string => _nodePath.resolve(p),
        normpath: (p: string): string => _nodePath.normalize(p),
        splitext: (p: string): [string, string] => {
            const ext  = _nodePath.extname(p);
            const base = ext ? p.slice(0, -ext.length) : p;
            return [base, ext];
        },
        split: (p: string): [string, string] => [
            _nodePath.dirname(p),
            _nodePath.basename(p),
        ],
        exists: (p: string): boolean => {
            try { _nodeFs.accessSync(p); return true; }
            catch { return false; }
        },
        isfile: (p: string): boolean => {
            try { return _nodeFs.statSync(p).isFile(); }
            catch { return false; }
        },
        isdir: (p: string): boolean => {
            try { return _nodeFs.statSync(p).isDirectory(); }
            catch { return false; }
        },
        sep: _nodePath.sep,
    },
    getcwd: (): string => {
        if (typeof process !== "undefined") return process.cwd();
        throw new RuntimeError("os.getcwd() is only available in Node.js environments");
    },
    getenv: (key: string, defaultVal: string = ""): string => {
        if (typeof process !== "undefined") return process.env[key] ?? defaultVal;
        throw new RuntimeError("os.getenv() is only available in Node.js environments");
    },
};


// ---------------------------------------------------------------------------
// Internal helpers (not exported)
// ---------------------------------------------------------------------------

function pyStr(x: any): string {
    if (x === null)          return "None";
    if (x === true)          return "True";
    if (x === false)         return "False";
    if (Array.isArray(x))    return `[${x.map(pyRepr).join(", ")}]`;
    if (x instanceof PyDict) return x.toString();
    return String(x);
}

function pyRepr(x: any): string {
    if (typeof x === "string") return `'${x}'`;
    return pyStr(x);
}

function pyEq(a: any, b: any): boolean {
    if (Array.isArray(a) && Array.isArray(b)) {
        return a.length === b.length && a.every((v, i) => pyEq(v, b[i]));
    }
    return a === b;
}

function pyCompare(a: any, b: any): number {
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
}

function pyType(x: any): string {
    return type(x);
}