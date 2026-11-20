// Calls to the backend's REST API (/api/v1), through the Vite proxy.

const BASE = '/api/v1';

export class ApiError extends Error {
	constructor(
		message: string,
		readonly status: number
	) {
		super(message);
	}
}

function csrfToken(): string {
	const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
	return match ? decodeURIComponent(match[1]) : '';
}

export async function api<T>(
	path: string,
	options: { method?: string; body?: unknown } = {}
): Promise<T> {
	const method = options.method ?? 'GET';
	const headers: Record<string, string> = {};
	if (options.body !== undefined) headers['Content-Type'] = 'application/json';
	if (method !== 'GET') headers['X-CSRF-Token'] = csrfToken();

	const response = await fetch(BASE + path, {
		method,
		headers,
		credentials: 'same-origin',
		body: options.body === undefined ? undefined : JSON.stringify(options.body)
	});
	const data = response.status === 204 ? null : await response.json().catch(() => null);
	if (!response.ok) {
		const detail = data && typeof data.detail === 'string' ? data.detail : response.statusText;
		throw new ApiError(detail || 'Something went wrong.', response.status);
	}
	return data as T;
}

export function socketUrl(path: string): string {
	const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
	return `${scheme}://${location.host}${BASE}${path}`;
}
