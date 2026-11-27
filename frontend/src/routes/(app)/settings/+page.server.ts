import { error, fail, redirect, type Cookies } from '@sveltejs/kit';
import * as v from 'valibot';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import { profileSchema } from '#lib/schemas/profile.ts';
import { resetPasswordSchema } from '#lib/schemas/password-reset.ts';
import { twoFactorCodeSchema } from '#lib/schemas/two-factor.ts';
import {
	api,
	jsonPost,
	jsonPatch,
	errorMessage,
	SESSION_COOKIE,
	CSRF_COOKIE
} from '#lib/server/api.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ cookies, fetch }) => {
	if (!cookies.get(SESSION_COOKIE)) {
		redirect(303, '/login');
	}

	let meResponse: Response;
	let twoFactorResponse: Response;

	try {
		[meResponse, twoFactorResponse] = await Promise.all([
			fetch(api('/users/me')),
			fetch(api('/auth/2fa'))
		]);
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (meResponse.status === 401 || twoFactorResponse.status === 401) {
		redirect(303, '/login');
	}

	if (!meResponse.ok) {
		error(502, 'Could not retrieve your account.');
	}

	if (!twoFactorResponse.ok) {
		error(502, 'Could not retrieve two-factor authentication status.');
	}

	// Response to JS Object
	const me: {
		username: string;
		email: string;
		avatar_url: string | null;
		created_at: string;
		has_password: boolean;
	} = await meResponse.json();
	const twoFactor: { enabled: boolean } = await twoFactorResponse.json();

	return {
		user: {
			username: me.username,
			email: me.email,
			avatarUrl: me.avatar_url?.startsWith('/')
				? `${PUBLIC_BACKEND_URL}${me.avatar_url}`
				: me.avatar_url,
			joined: new Date(me.created_at).toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			}),
			hasPassword: me.has_password
		},
		twoFactorEnabled: twoFactor.enabled
	};
};

const AVATAR_MAX_BYTES = 2 * 1024 * 1024; // same limit as the backend

// Changing email or password makes the backend end the session, so we send the
// person to the login page and show them a message there.
function signOutAfterUpdate(cookies: Cookies): never {
	cookies.delete(SESSION_COOKIE, { path: '/' });
	cookies.delete(CSRF_COOKIE, { path: '/' });
	redirect(303, '/login?account_updated=1');
}

// Sends a request to FastAPI. Returns the response, or an error message to show on the page.
async function callBackend(
	fetch: typeof globalThis.fetch,
	path: string,
	init: RequestInit,
	fallback: string
) {
	let response: Response;

	try {
		response = await fetch(api(path), init);
	} catch {
		return {
			status: 502,
			error: 'Cannot connect to the server. Please try again.'
		};
	}

	if (response.status === 401) {
		redirect(303, '/login');
	}

	if (!response.ok) {
		return {
			status: response.status,
			error: await errorMessage(response, fallback)
		};
	}

	return { status: response.status, error: null };
}

type TwoFactorAction = 'enable' | 'disable';

function getAction(data: FormData): TwoFactorAction | null {
	const action = data.get('action');

	return action === 'enable' || action === 'disable' ? action : null;
}

export const actions = {
	updateProfile: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const data = await request.formData();
		const values = {
			username: String(data.get('username') ?? ''),
			email: String(data.get('email') ?? '')
		};
		const section = 'profile';

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, { section, error: 'CSRF token missing. Please log in again.', values });
		}

		const result = v.safeParse(profileSchema, values);

		if (!result.success) {
			return fail(400, { section, error: result.issues[0].message, values });
		}

		// Only send what changed, so nobody is signed out for nothing
		const changes: { username?: string; email?: string } = {};
		let current: Response;

		try {
			current = await fetch(api('/users/me'));
		} catch {
			return fail(502, {
				section,
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (current.status === 401) {
			redirect(303, '/login');
		}

		if (!current.ok) {
			return fail(502, {
				section,
				error: 'Could not retrieve your account. Please try again.',
				values
			});
		}

		const me: { username: string; email: string } = await current.json();

		if (me?.username !== result.output.username) {
			changes.username = result.output.username;
		}

		if (me?.email !== result.output.email) {
			changes.email = result.output.email;
		}

		// Object.keys(changes) lists property names, an empty object has 0 keys,
		// so there is nothing to save and no PATCH request is needed.
		if (!Object.keys(changes).length) {
			return fail(400, { section, error: 'There is nothing to save yet.', values });
		}

		const outcome = await callBackend(
			fetch,
			'/users/me',
			jsonPatch(changes),
			'Could not update your profile. Please try again.'
		);

		if (outcome.error) {
			return fail(outcome.status, { section, error: outcome.error, values });
		}

		if (changes.email) {
			signOutAfterUpdate(cookies);
		}

		return {
			section,
			error: null,
			message: 'Profile updated successfully.'
		};
	},

	changePassword: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const section = 'password';

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, { section, error: 'CSRF token missing. Please log in again.' });
		}

		const data = await request.formData();
		const result = v.safeParse(resetPasswordSchema, {
			newPassword: String(data.get('new-password') ?? ''),
			confirmPassword: String(data.get('confirm-password') ?? '')
		});

		if (!result.success) {
			return fail(400, { section, error: result.issues[0].message });
		}

		const outcome = await callBackend(
			fetch,
			'/users/me',
			jsonPatch({
				password: result.output.newPassword,
				current_password: String(data.get('current-password') ?? '')
			}),
			'Could not change your password. Please try again.'
		);

		if (outcome.error) {
			return fail(outcome.status, { section, error: outcome.error });
		}

		signOutAfterUpdate(cookies);
	},

	uploadAvatar: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const section = 'avatar';

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, { section, error: 'CSRF token missing. Please log in again.' });
		}

		const file = (await request.formData()).get('file');

		if (!(file instanceof File) || file.size === 0) {
			return fail(400, { section, error: 'Choose an image first.' });
		}

		if (file.size > AVATAR_MAX_BYTES) {
			return fail(413, { section, error: 'Avatar must be at most 2 MB.' });
		}

		const body = new FormData();
		body.append('file', file);

		const outcome = await callBackend(
			fetch,
			'/users/me/avatar',
			{ method: 'PUT', body },
			'Could not upload your avatar. Please try again.'
		);

		if (outcome.error) {
			return fail(outcome.status, { section, error: outcome.error });
		}

		return { section, error: null, message: 'Avatar updated.' };
	},

	removeAvatar: async ({ fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const section = 'avatar';

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, { section, error: 'CSRF token missing. Please log in again.' });
		}

		const outcome = await callBackend(
			fetch,
			'/users/me/avatar',
			{ method: 'DELETE' },
			'Could not remove your avatar. Please try again.'
		);

		if (outcome.error) {
			return fail(outcome.status, { section, error: outcome.error });
		}

		return { section, error: null, message: 'Avatar removed.' };
	},

	requestCode: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				section: 'twoFactor',
				step: null,
				action: null,
				error: 'CSRF token missing. Please log in again.'
			});
		}

		const data = await request.formData();
		const action = getAction(data);

		if (!action) {
			return fail(400, {
				section: 'twoFactor',
				step: null,
				action: null,
				error: 'Invalid two-factor authentication action.'
			});
		}

		let response: Response;

		try {
			response = await fetch(api('/auth/2fa/code'), jsonPost({ action }));
		} catch {
			return fail(502, {
				section: 'twoFactor',
				step: null,
				action,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) {
			redirect(303, '/login');
		}

		if (!response.ok) {
			return fail(response.status, {
				section: 'twoFactor',
				step: null,
				action,
				error: await errorMessage(response, 'Something went wrong. Please try again.')
			});
		}

		return {
			section: 'twoFactor',
			step: 'code',
			action,
			error: null
		};
	},

	confirmCode: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				section: 'twoFactor',
				step: null,
				action: null,
				error: 'CSRF token missing. Please log in again.'
			});
		}

		const data = await request.formData();
		const action = getAction(data);

		if (!action) {
			return fail(400, {
				section: 'twoFactor',
				step: null,
				action: null,
				error: 'Invalid two-factor authentication action.'
			});
		}

		const code = String(data.get('code') ?? '');
		const result = v.safeParse(twoFactorCodeSchema, { code });

		if (!result.success) {
			return fail(400, {
				section: 'twoFactor',
				step: 'code',
				action,
				error: result.issues[0].message
			});
		}

		let response: Response;

		try {
			response = await fetch(api(`/auth/2fa/${action}`), jsonPost(result.output));
		} catch {
			return fail(502, {
				section: 'twoFactor',
				step: 'code',
				action,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) {
			redirect(303, '/login');
		}

		if (!response.ok) {
			return fail(response.status, {
				section: 'twoFactor',
				step: 'code',
				action,
				error: await errorMessage(response, 'Something went wrong. Please try again.')
			});
		}

		redirect(303, '/settings?two_factor_updated=1');
	}
} satisfies Actions;
