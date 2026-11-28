import { error, fail, redirect } from '@sveltejs/kit';
import { api, errorMessage, SESSION_COOKIE, CSRF_COOKIE } from '#lib/server/api.ts';
import type { Actions, PageServerLoad } from './$types';
import {
	toFriend,
	type FriendResponse,
	type PaginatedResponse
} from '#lib/server/profile-friends.ts';

const PAGE_SIZE = 8;

export const load: PageServerLoad = async ({ fetch, parent, url }) => {
	await parent();

	const query = (url.searchParams.get('q') ?? '').trim();

	if (query.length > 32) {
		error(400, 'Search must be at most 32 characters.');
	}

	const requestedPage = Number(url.searchParams.get('page') ?? 1);
	const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;

	const params = new URLSearchParams({
		page: String(page),
		size: String(PAGE_SIZE)
	});

	if (query) {
		params.set('q', query);
	}

	let response: Response;

	try {
		response = await fetch(api(`/friends?${params.toString()}`));
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

	// redirects to the last valid page
	if (page > Math.max(1, friends.pages)) {
		const lastPage = Math.max(1, friends.pages);
		const redirectParams = new URLSearchParams({ page: String(lastPage) });

		if (query) {
			redirectParams.set('q', query);
		}

		redirect(302, `/profile/friends?${redirectParams.toString()}`);
	}

	return {
		friendCount: friends.total,
		friends: friends.items.map(toFriend),
		page,
		pages: friends.pages,
		query
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
