// The signed-in user, shared by every page.
import { api } from '#lib/api.ts';

export type User = {
	id: string;
	username: string;
	email: string;
	avatar_url: string | null;
	role: 'USER' | 'GAME_MASTER';
};

export const session = $state<{ user: User | null; checked: boolean }>({
	user: null,
	checked: false
});

export async function loadUser(): Promise<User | null> {
	try {
		session.user = await api<User>('/users/me');
	} catch {
		session.user = null;
	}
	session.checked = true;
	return session.user;
}

export async function logout(): Promise<void> {
	try {
		await api('/auth/logout', { method: 'POST' });
	} finally {
		session.user = null;
	}
}
