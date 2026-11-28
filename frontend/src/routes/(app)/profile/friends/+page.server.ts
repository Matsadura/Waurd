import { PUBLIC_BACKEND_URL } from '$app/env/public';
import { error, fail, redirect } from '@sveltejs/kit';
import {
	api,
	jsonPost,
	jsonPatch,
	errorMessage,
	SESSION_COOKIE,
	CSRF_COOKIE
} from '#lib/server/api.ts';
import type { Friend } from '#lib/types/profile.ts';
import type { Actions, PageServerLoad } from './$types';

type FriendResponse = {
	id: string;
	username: string;
	avatar_url: string | null;
	is_online: boolean;
	last_seen_at: string | null;
};

type PendingRequestResponse = FriendResponse & {
	request_id: number;
	requested_at: string;
};

type PaginatedResponse<T> = {
	items: T[];
	total: number;
};

function toFriend(user: FriendResponse): Friend {
	return {
		id: user.id,
		username: user.username,
		avatarUrl: user.avatar_url?.startsWith('/')
			? `${PUBLIC_BACKEND_URL}${user.avatar_url}`
			: (user.avatar_url ?? undefined),
		online: user.is_online,
		lastSeen: user.last_seen_at
			? new Date(user.last_seen_at).toLocaleString('en-US', {
					month: 'short',
					day: 'numeric',
					hour: 'numeric',
					minute: '2-digit'
				})
			: undefined
	};
}

export const load: PageServerLoad = async ({ fetch, parent }) => {
	await parent();

	let friendsResponse: Response;
	let incomingResponse: Response;
	let outgoingResponse: Response;

	try {
		[friendsResponse, incomingResponse, outgoingResponse] = await Promise.all([
			fetch(api('/friends?page=1&size=100')),
			fetch(api('/friends/requests?direction=incoming&page=1&size=100')),
			fetch(api('/friends/requests?direction=outgoing&page=1&size=100'))
		]);
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (
		friendsResponse.status === 401 ||
		incomingResponse.status === 401 ||
		outgoingResponse.status === 401
	) {
		redirect(303, '/login');
	}

	if (!friendsResponse.ok || !incomingResponse.ok || !outgoingResponse.ok) {
		error(502, 'Could not retrieve your friends.');
	}

	const friends: PaginatedResponse<FriendResponse> = await friendsResponse.json();
	const incoming: PaginatedResponse<PendingRequestResponse> = await incomingResponse.json();
	const outgoing: PaginatedResponse<PendingRequestResponse> = await outgoingResponse.json();

	return {
		friendCount: friends.total,
		friends: friends.items.map(toFriend),
		incoming: incoming.items.map((request) => ({
			...toFriend(request),
			requestId: request.request_id
		})),
		outgoing: outgoing.items.map((request) => ({
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
	},

	removeFriend: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		const section = 'removeFriend';
		const data = await request.formData();
		const friendId = String(data.get('friendId') ?? '');

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				section,
				error: 'CSRF token missing. Please log in again.'
			});
		}

		if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(friendId)) {
			return fail(400, {
				section,
				error: 'Invalid friend ID.'
			});
		}

		let response: Response;

		try {
			response = await fetch(api(`/friends/${friendId}`), { method: 'DELETE' });
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
				error: await errorMessage(response, 'Could not remove friend.')
			});
		}

		return {
			section,
			error: null,
			message: 'Friend removed.'
		};
	}
} satisfies Actions;
