import { BACKEND_URL } from '$app/env/private';
import { fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { twoFactorCodeSchema } from '#lib/schemas/two-factor.ts';
import type { Actions, PageServerLoad } from './$types';

function extractError(json: unknown): string {
	if (
		typeof json === 'object' &&
		json !== null &&
		'detail' in json &&
		typeof json.detail === 'string'
	) {
		return json.detail;
	}

	return 'Verification failed. Please try again.';
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

export const load: PageServerLoad = ({ cookies }) => {
	if (!cookies.get('two_factor_token')) {
		redirect(303, '/login');
	}
};

export const actions = {
	default: async ({ request, fetch, cookies }) => {
		const twoFactorToken = cookies.get('two_factor_token');

		if (!twoFactorToken) {
			redirect(303, '/login');
		}

		const data = await request.formData();
		const code = String(data.get('code') ?? '');

		const result = v.safeParse(twoFactorCodeSchema, { code });

		if (!result.success) {
			return fail(400, {
				error: result.issues[0].message
			});
		}

		let response: Response;

		try {
			response = await fetch(`${BACKEND_URL}/api/v1/auth/2fa/verify`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Cookie: `two_factor_token=${twoFactorToken}`
				},
				body: JSON.stringify(result.output)
			});
		} catch {
			return fail(502, {
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (!response.ok) {
			const json = await response.json().catch(() => null);

			return fail(response.status, {
				error: extractError(json)
			});
		}

		const setCookieHeaders = response.headers.getSetCookie();
		const sessionId = getCookieValue(setCookieHeaders, 'session_id');
		const csrfToken = getCookieValue(setCookieHeaders, 'csrf_token');

		if (!sessionId || !csrfToken) {
			return fail(502, {
				error: 'Could not establish your session. Please try again.'
			});
		}

		const maxAge = 60 * 60 * 24 * 7;

		cookies.set('session_id', sessionId, {
			path: '/',
			httpOnly: true,
			secure: false, // Local development over HTTP
			sameSite: 'lax',
			maxAge
		});

		cookies.set('csrf_token', csrfToken, {
			path: '/',
			httpOnly: false,
			secure: false, // Local development over HTTP
			sameSite: 'lax',
			maxAge
		});

		cookies.delete('two_factor_token', { path: '/' });

		redirect(303, '/play');
	}
} satisfies Actions;