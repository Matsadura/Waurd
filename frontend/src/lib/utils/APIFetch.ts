import { PUBLIC_BACKEND_URL } from '$app/env/public';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

function getCookie(name: string): string {
	if (typeof document === 'undefined') return '';
	const prefix = `${name}=`;
	const cookie = document.cookie.split('; ').find((c) => c.startsWith(prefix));
	return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : '';
}

export async function APIFetch(
	method: HttpMethod,
	path: string,
	body?: object,
) {
	const normalizedPath = path.startsWith('/') ? path : `/${path}`;
	const headers: Record<string, string> = {};

	if (body !== undefined) {
		headers['Content-Type'] = 'application/json';
	}

	if (method !== 'GET') {
		const csrf = getCookie('csrf_token');
		if (csrf) {
			headers['X-CSRF-Token'] = csrf;
		}
	}

	return fetch(`${PUBLIC_BACKEND_URL}/api/v1${normalizedPath}`, {
		method,
		headers,
		credentials: 'include',
		body: body ? JSON.stringify(body) : undefined,
	});
}