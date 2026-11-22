// Goldline (v4.1.1-goldline.8): every value that ends up in an input's pattern attribute compiles with the v flag,
// which is how Chrome and Firefox now compile pattern attributes (an invalid one logs a console error).
import { readdirSync, readFileSync, statSync } from 'fs';
import path from 'path';
import { describe, expect, it } from 'vitest';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import * as schemas from './schemas';
import { mfaAuthenticateSchema } from '../../routes/(authentication)/login/mfa/utils/schemas';

function patternsIn(node: unknown, out: string[] = []): string[] {
	if (node && typeof node === 'object') {
		for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
			if (k === 'pattern' && typeof v === 'string') out.push(v);
			else patternsIn(v, out);
		}
	}
	return out;
}

function compilesWithV(p: string): boolean {
	try {
		new RegExp(p, 'v');
		return true;
	} catch {
		return false;
	}
}

function svelteFiles(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const full = path.join(dir, name);
		if (statSync(full).isDirectory()) svelteFiles(full, out);
		else if (full.endsWith('.svelte')) out.push(full);
	}
	return out;
}

describe('pattern attributes compile with the v flag', () => {
	it('the email pattern is valid with the v flag and accepts the same addresses as before', () => {
		expect(compilesWithV(schemas.EMAIL_PATTERN.source)).toBe(true);
		const v = new RegExp(schemas.EMAIL_PATTERN.source, 'v');
		for (const ok of ['a@b.co', 'first.last@example.co.uk', "o'neil+tag@x.io", 'a-b_c@sub.do-main.org']) {
			expect(v.test(ok), ok).toBe(true);
		}
		for (const bad of ['a@b', '.a@b.co', 'a..b@c.co', 'a@-b.co', 'a b@c.co', 'a@b.c']) {
			expect(v.test(bad), bad).toBe(false);
		}
	});

	it('the email fields carry the v-safe pattern', () => {
		const c = zod(schemas.loginSchema).constraints as Record<string, { pattern?: string }>;
		expect(c.username.pattern).toBe(schemas.EMAIL_PATTERN.source);
	});

	it('every pattern constraint generated from the form schemas compiles with the v flag', () => {
		const all = { ...schemas, mfaAuthenticateSchema } as Record<string, unknown>;
		const bad: string[] = [];
		let checked = 0;
		for (const [name, schema] of Object.entries(all)) {
			if (!schema || typeof schema !== 'object' || !('_zod' in (schema as object))) continue;
			let constraints: unknown;
			try {
				constraints = zod(schema as never).constraints;
			} catch {
				continue; // not an object schema a form can be built from
			}
			for (const p of patternsIn(constraints)) {
				checked++;
				if (!compilesWithV(p)) bad.push(`${name}: ${p}`);
			}
		}
		expect(checked).toBeGreaterThan(0);
		expect(bad).toEqual([]);
	});

	it('every literal pattern attribute in the components compiles with the v flag', () => {
		const root = path.resolve(__dirname, '..', '..');
		const bad: string[] = [];
		for (const file of svelteFiles(root)) {
			const text = readFileSync(file, 'utf8');
			for (const m of text.matchAll(/\bpattern="([^"{]+)"/g)) {
				if (!compilesWithV(m[1])) bad.push(`${path.relative(root, file)}: ${m[1]}`);
			}
			for (const m of text.matchAll(/\bpattern:\s*'([^']+)'/g)) {
				const p = m[1].replace(/\\\\/g, '\\');
				if (!compilesWithV(p)) bad.push(`${path.relative(root, file)}: ${p}`);
			}
		}
		expect(bad).toEqual([]);
	});
});
