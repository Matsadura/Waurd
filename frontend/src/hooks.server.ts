import type { Handle, HandleFetch } from '@sveltejs/kit/hooks';
import { BACKEND_URL } from '$app/env/private';
import { PUBLIC_BACKEND_URL } from '$app/env/public';

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	if (request.url.startsWith(PUBLIC_BACKEND_URL)) {
		request = new Request(request.url.replace(PUBLIC_BACKEND_URL, BACKEND_URL), request);

		const cookie = event.request.headers.get('cookie');
		if (cookie) {
			request.headers.set('cookie', cookie);
		}

		const csrf = event.cookies.get('csrf_token');
		if (csrf) {
			request.headers.set('X-CSRF-Token', csrf);
		}
	}

	return fetch(request);
};

/** Hook to handle user auth */
export const handle: Handle = async ({ event, resolve }) => {
	// Skip the backend call if the browser sent no cookies at all
	if (!event.request.headers.get('cookie')) {
		event.locals.user = null;
		return resolve(event);
	}

	const res = await event.fetch(`${PUBLIC_BACKEND_URL}/api/v1/users/me`);
	event.locals.user = res.ok ? await res.json() : null;

	return resolve(event);
};
