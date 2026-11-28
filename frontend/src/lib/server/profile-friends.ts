import { PUBLIC_BACKEND_URL } from '$app/env/public';
import type { Friend } from '#lib/types/profile.ts';

export type FriendResponse = {
	id: string;
	username: string;
	avatar_url: string | null;
	is_online: boolean;
	last_seen_at: string | null;
};

export type PaginatedResponse<T> = {
	items: T[];
	total: number;
	pages: number;
};

export function toFriend(user: FriendResponse): Friend {
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
