import { PUBLIC_BACKEND_URL } from '$app/env/public';
import { error, fail, redirect } from '@sveltejs/kit';
import { api, errorMessage, SESSION_COOKIE, CSRF_COOKIE } from '#lib/server/api.ts';
import type { Friend } from '#lib/types/profile.ts';
import type { Actions, PageServerLoad } from './$types';

type FriendResponse = {
	id: string;
	username: string;
	avatar_url: string | null;
	is_online: boolean;
	last_seen_at: string | null;
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

	let response: Response;

	try {
		response = await fetch(api('/friends?page=1&size=100'));
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (response.status === 401) {
		redirect(303, '/login');
	}

	if (!response.ok) {
		error(502, 'Could not retrieve your friends.');
	}

	const friends: PaginatedResponse<FriendResponse> = await response.json();

	return {
		friendCount: friends.total,
		friends: friends.items.map(toFriend)
	};
};

export const actions = {
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
