import { describe, expect, it } from 'vitest';
import { outcomeOfError, outcomeOfStatus } from './background-fetch';

describe('background fetch outcomes (FND-283)', () => {
	it('treats 2xx as usable', () => {
		expect(outcomeOfStatus(200)).toBe('ok');
		expect(outcomeOfStatus(204)).toBe('ok');
	});

	it('stops quietly when signed out, refused or missing', () => {
		expect(outcomeOfStatus(401)).toBe('stop');
		expect(outcomeOfStatus(403)).toBe('stop');
		expect(outcomeOfStatus(404)).toBe('stop');
	});

	it('reports server errors as failures', () => {
		expect(outcomeOfStatus(500)).toBe('failed');
		expect(outcomeOfStatus(502)).toBe('failed');
	});

	it('says nothing when the request was aborted', () => {
		const abort = Object.assign(new Error('aborted'), { name: 'AbortError' });
		expect(outcomeOfError(abort)).toBe('interrupted');
		expect(outcomeOfError(abort, true)).toBe('interrupted');
	});

	it('says nothing for a network TypeError while the page is leaving (Safari "Load failed", Firefox NetworkError)', () => {
		expect(outcomeOfError(new TypeError('Load failed'), true)).toBe('interrupted');
		expect(
			outcomeOfError(new TypeError('NetworkError when attempting to fetch resource.'), true)
		).toBe('interrupted');
	});

	it('still reports a network TypeError on a page that stays', () => {
		expect(outcomeOfError(new TypeError('Load failed'), false)).toBe('failed');
	});

	it('reports anything else as a failure', () => {
		expect(outcomeOfError(new Error('boom'))).toBe('failed');
		expect(outcomeOfError(null)).toBe('failed');
	});
});
