// Goldline (v4.1.1-goldline.5): a requirement the user may not see is a clean 404, never a server error.
import { describe, expect, it } from 'vitest';
import { load } from './+page.server';

const notFound = async () => new Response(JSON.stringify({ detail: 'Not found.' }), { status: 404 });
const forbidden = async () => new Response(JSON.stringify({ detail: 'Forbidden' }), { status: 403 });

describe('requirement page of another domain', () => {
	it('answers 404 when the API says not found', async () => {
		await expect(load({ fetch: notFound, params: { id: '00000000-0000-0000-0000-000000000000' } } as never)).rejects.toMatchObject({ status: 404 });
	});
	it('answers 404 when the API refuses access', async () => {
		await expect(load({ fetch: forbidden, params: { id: '00000000-0000-0000-0000-000000000000' } } as never)).rejects.toMatchObject({ status: 404 });
	});
});
