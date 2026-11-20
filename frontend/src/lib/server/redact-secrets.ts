// Goldline (v4.1.1-goldline.6, FND-271): a form returned by an authentication action never carries back the
// password, token or code the user submitted. Every such field is blanked before the form is returned.

export const SECRET_FIELDS = [
	'password',
	'old_password',
	'new_password',
	'confirm_new_password',
	'code',
	'token',
	'uidb64'
] as const;

export function blankSecrets<T extends { data: Record<string, unknown> }>(form: T): T {
	for (const field of SECRET_FIELDS) {
		if (field in form.data) form.data[field] = '';
	}
	return form;
}
