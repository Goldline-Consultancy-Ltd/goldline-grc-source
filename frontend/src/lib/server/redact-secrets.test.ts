// Goldline (v4.1.1-goldline.6, FND-271): no authentication action returns the password, token or code the user sent.
import { describe, expect, it, vi } from 'vitest';

vi.mock('$lib/server/logger', () => ({
	logger: { debug: vi.fn(), info: vi.fn(), warning: vi.fn(), error: vi.fn(), critical: vi.fn() }
}));

import { actions as loginActions } from '../../routes/(authentication)/login/+page.server';
import { actions as firstConnexionActions } from '../../routes/(authentication)/first-connexion/+page.server';
import { actions as resetConfirmActions } from '../../routes/(authentication)/password-reset/confirm/+page.server';
import { actions as changePasswordActions } from '../../routes/(app)/(third-party)/my-profile/change-password/+page.server';
import { actions as setPasswordActions } from '../../routes/(app)/(internal)/users/[id=uuid]/edit/set-password/+page.server';
import { actions as setupMfaActions } from '../../routes/(app)/setup-mfa/+page.server';
import { actions as profileSettingsActions } from '../../routes/(app)/(third-party)/my-profile/settings/+page.server';
import { blankSecrets } from './redact-secrets';

const SECRET = 'Sup3r-Secret-Pa55word!';
const CODE = '123456';

function post(fields: Record<string, string>, url = 'http://localhost/x?token=tok-SECRET&uidb64=uid-SECRET') {
	const body = new FormData();
	for (const [k, v] of Object.entries(fields)) body.append(k, v);
	return new Request(url, { method: 'POST', body });
}

function event(fields: Record<string, string>, apiBody: unknown, apiStatus = 400) {
	const request = post(fields);
	return {
		request,
		url: new URL(request.url),
		params: { id: '00000000-0000-0000-0000-000000000000' },
		cookies: { set: vi.fn(), get: vi.fn(), delete: vi.fn() },
		locals: {},
		fetch: vi.fn(async () => new Response(JSON.stringify(apiBody), { status: apiStatus }))
	} as never;
}

function assertNoSecret(result: unknown) {
	const text = JSON.stringify(result);
	expect(text).not.toContain(SECRET);
	expect(text).not.toContain(CODE);
	expect(text).not.toContain('tok-SECRET');
	expect(text).not.toContain('uid-SECRET');
}

describe('blankSecrets', () => {
	it('blanks every secret field and keeps the others', () => {
		const form = { data: { username: 'a@b.c', password: SECRET, code: CODE, user: 'u1' } };
		blankSecrets(form);
		expect(form.data).toEqual({ username: 'a@b.c', password: '', code: '', user: 'u1' });
	});
});

describe('sign-in', () => {
	it('wrong password: the returned form holds no password', async () => {
		const r = await loginActions.login(
			event({ username: 'user@tests.com', password: SECRET }, { status: 400, errors: [{ param: 'password', code: 'incorrect' }] })
		);
		expect((r as { status: number }).status).toBe(400);
		assertNoSecret(r);
	});
	it('invalid form: the returned form holds no password', async () => {
		const r = await loginActions.login(event({ username: 'not-an-email', password: SECRET }, {}));
		assertNoSecret(r);
	});
	it('MFA step: the returned form holds no password', async () => {
		const r = await loginActions.login(
			event({ username: 'user@tests.com', password: SECRET }, {
				status: 401,
				data: { flows: [{ id: 'mfa_authenticate', is_pending: true, types: ['totp'] }] },
				meta: { session_token: 'session' }
			})
		);
		expect((r as { mfa: boolean }).mfa).toBe(true);
		assertNoSecret(r);
	});
	it('MFA code refused: the returned form holds no code', async () => {
		const r = await loginActions.mfaAuthenticate(event({ code: CODE }, { status: 400, errors: [{ param: 'code', code: 'incorrect_code' }] }));
		assertNoSecret(r);
	});
	it('MFA code accepted: the returned form holds no code', async () => {
		const r = await loginActions.mfaAuthenticate(
			event({ code: CODE }, { status: 200, meta: { access_token: 'a', session_token: 's' } }, 200)
		);
		assertNoSecret(r);
	});
});

describe('password set, reset and change', () => {
	const fields = { new_password: SECRET, confirm_new_password: SECRET };
	const refused = { new_password: ['too weak'] };
	it('first connexion', async () => {
		assertNoSecret(await firstConnexionActions.default(event(fields, refused)));
	});
	it('password reset confirm', async () => {
		assertNoSecret(await resetConfirmActions.default(event(fields, refused)));
	});
	it('password change', async () => {
		assertNoSecret(await changePasswordActions.default(event({ old_password: SECRET, ...fields }, refused)));
	});
	it('administrator sets a password', async () => {
		assertNoSecret(await setPasswordActions.default(event({ user: 'u1', ...fields }, refused)));
	});
});

describe('TOTP activation', () => {
	const refused = { status: 400, errors: [{ param: 'code', code: 'incorrect_code', message: 'Incorrect code.' }] };
	it('setup page', async () => {
		assertNoSecret(await setupMfaActions.activateTOTP(event({ code: CODE }, refused)));
	});
	it('profile settings page', async () => {
		assertNoSecret(await profileSettingsActions.activateTOTP(event({ code: CODE }, refused)));
	});
});
