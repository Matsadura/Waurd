import { BACKEND_URL } from '$app/env/private';
import { fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { loginSchema } from '#lib/schemas/login.ts';
import type { Actions } from './$types';

function extractError(json: unknown): string {
	if (
		typeof json === 'object' &&
		json !== null &&
		'detail' in json &&
		typeof json.detail === 'string'
	) {
		return json.detail;
	}

	return 'Login failed. Please try again.';
}

function getCookieValue(headers: string[], name: string): string | null {
	for (const header of headers) {
		const [cookie] = header.split(';', 1);
		const separator = cookie.indexOf('=');

		if (separator === -1) continue;

		if (cookie.slice(0, separator) === name) {
			return cookie.slice(separator + 1);
		}
	}

	return null;
}

export const actions = {
	default: async ({ request, fetch, cookies }) => {
		const data = await request.formData();

		const email = String(data.get('email') ?? '');
		const password = String(data.get('password') ?? '');
		const values = { email };

		const result = v.safeParse(loginSchema, { email, password });

		if (!result.success) {
			return fail(400, {
				error: result.issues[0].message,
				values
			});
		}

		let response: Response;

		try {
			response = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(result.output)
			});
		} catch {
			return fail(502, {
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (!response.ok) {
			const json = await response.json().catch(() => null);

			return fail(response.status, {
				error: extractError(json),
				values
			});
		}

		if (response.status === 202) { // it provides only two_factor_token
			const twoFactorToken = getCookieValue(
				response.headers.getSetCookie(),
				'two_factor_token'
			);

			if (!twoFactorToken) {
				return fail(502, {
					error: 'Could not start two-factor verification. Please try again.',
					values
				});
			}

			cookies.set('two_factor_token', twoFactorToken, {
				path: '/',
				httpOnly: true,
				secure: false, // Local development over HTTP
				sameSite: 'lax',
				maxAge: 600
			});

			redirect(303, '/verify-2fa');
		}

		const setCookieHeaders = response.headers.getSetCookie();
		const sessionId = getCookieValue(setCookieHeaders, 'session_id');
		const csrfToken = getCookieValue(setCookieHeaders, 'csrf_token');

		if (!sessionId || !csrfToken) {
			return fail(502, {
				error: 'Could not establish your session. Please try again.',
				values
			});
		}

		const maxAge = 60 * 60 * 24 * 7;

		cookies.set('session_id', sessionId, {
			path: '/',
			httpOnly: true,
			secure: false, // TODO: Use secure cookies in production (HTTPS)
			sameSite: 'lax',
			maxAge
		});

		cookies.set('csrf_token', csrfToken, {
			path: '/',
			httpOnly: false,
			secure: false, // TODO: Use secure cookies in production (HTTPS)
			sameSite: 'lax',
			maxAge
		});

		// TODO: Redirect to /play once the app routes are merged
		redirect(303, '/play');
	}
} satisfies Actions;
