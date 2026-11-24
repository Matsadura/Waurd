import { PUBLIC_BACKEND_URL } from '$app/env/public';

export async function APIFetch(method: 'GET' | 'POST' | 'DELETE', path: string, body?: object) {
	const csrf = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)?.[1] ?? '';
	if (path[0] != '/') {
		console.warn('at:', path, "- path should start with leading '/'");
	}
	return fetch(`${PUBLIC_BACKEND_URL}/api/v1` + path, {
		method,
		headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': decodeURIComponent(csrf) },
		credentials: 'include',
		body: body && JSON.stringify(body)
	});
}
