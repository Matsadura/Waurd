import { error, fail, redirect } from '@sveltejs/kit';
import {
	api,
	jsonPost,
	jsonPatch,
	errorMessage,
	SESSION_COOKIE,
	CSRF_COOKIE
} from '#lib/server/api.ts';
import {
	toFriend,
	type FriendResponse,
	type PaginatedResponse
} from '#lib/server/profile-friends.ts';
import type { Actions, PageServerLoad } from './$types';

type PendingRequestResponse = FriendResponse & {
	request_id: number;
	requested_at: string;
};

const PAGE_SIZE = 8;

export const load: PageServerLoad = async ({ fetch, parent, url }) => {
	await parent();

	const tab = url.searchParams.get('tab') === 'sent' ? 'sent' : 'received';

	const requestedPage = Number(url.searchParams.get('page') ?? 1);
	const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;

	const direction = tab === 'received' ? 'incoming' : 'outgoing';

	let response: Response;

	try {
		response = await fetch(
			api(`/friends/requests?direction=${direction}&page=${page}&size=${PAGE_SIZE}`)
		);
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (response.status === 401) {
		redirect(303, '/login');
	}

	if (!response.ok) {
		error(502, 'Could not retrieve your friend requests.');
	}

	const result: PaginatedResponse<PendingRequestResponse> = await response.json();

	const lastPage = Math.max(1, result.pages);

	if (page > lastPage) {
		redirect(302, `/profile/friends/requests?tab=${tab}&page=${lastPage}`);
	}

	return {
		tab,
		page,
		pages: result.pages,
		total: result.total,
		requests: result.items.map((request) => ({
			...toFriend(request),
			requestId: request.request_id
		}))
	};
};

export const actions = {
	sendRequest: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const section = 'sendRequest';
		const data = await request.formData();
		const username = String(data.get('username') ?? '').trim();
		const values = { username };

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				section,
				error: 'CSRF token missing. Please log in again.',
				values
			});
		}

		if (username.length < 3 || username.length > 32) {
			return fail(400, {
				section,
				error: 'Username must be between 3 and 32 characters.',
				values
			});
		}

		let response: Response;

		try {
			response = await fetch(api('/friends/requests'), jsonPost({ username }));
		} catch {
			return fail(502, {
				section,
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (response.status === 401) {
			redirect(303, '/login');
		}

		if (!response.ok) {
			return fail(response.status, {
				section,
				error: await errorMessage(response, 'Could not send friend request.'),
				values
			});
		}

		return {
			section,
			error: null,
			message: `Friend request sent to ${username}.`,
			values: { username: '' }
		};
	},

	respondRequest: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const section = 'respondRequest';
		const data = await request.formData();

		const requestId = Number(data.get('requestId'));
		const action = String(data.get('action') ?? '');

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				section,
				error: 'CSRF token missing. Please log in again.'
			});
		}

		if (!Number.isSafeInteger(requestId) || requestId <= 0) {
			return fail(400, {
				section,
				error: 'Invalid friend request ID.'
			});
		}

		if (action !== 'ACCEPTED' && action !== 'DECLINED') {
			return fail(400, {
				section,
				error: 'Invalid friend request action.'
			});
		}

		let response: Response;

		try {
			response = await fetch(api(`/friends/requests/${requestId}`), jsonPatch({ action }));
		} catch {
			return fail(502, {
				section,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) {
			redirect(303, '/login');
		}

		if (!response.ok) {
			return fail(response.status, {
				section,
				error: await errorMessage(response, 'Could not process friend request.')
			});
		}

		return {
			section,
			error: null,
			message: action === 'ACCEPTED' ? 'Friend request accepted.' : 'Friend request declined.'
		};
	},

	withdrawRequest: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const section = 'withdrawRequest';
		const data = await request.formData();
		const requestId = Number(data.get('requestId'));

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				section,
				error: 'CSRF token missing. Please log in again.'
			});
		}

		if (!Number.isSafeInteger(requestId) || requestId <= 0) {
			return fail(400, {
				section,
				error: 'Invalid friend request ID.'
			});
		}

		let response: Response;

		try {
			response = await fetch(api(`/friends/requests/${requestId}`), { method: 'DELETE' });
		} catch {
			return fail(502, {
				section,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) {
			redirect(303, '/login');
		}

		if (!response.ok) {
			return fail(response.status, {
				section,
				error: await errorMessage(response, 'Could not withdraw friend request.')
			});
		}

		return {
			section,
			error: null,
			message: 'Friend request withdrawn.'
		};
	}
} satisfies Actions;
