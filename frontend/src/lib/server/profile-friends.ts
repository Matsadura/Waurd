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

function timeAgo(value: string): string {
	const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));

	if (minutes < 1) return 'just now';
	if (minutes < 60) return `${minutes} min ago`;

	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;

	const days = Math.floor(hours / 24);
	return `${days} ${days === 1 ? 'day' : 'days'} ago`;
}

export function toFriend(user: FriendResponse): Friend {
	return {
		id: user.id,
		username: user.username,
		avatarUrl: user.avatar_url?.startsWith('/')
			? `${PUBLIC_BACKEND_URL}${user.avatar_url}`
			: (user.avatar_url ?? undefined),
		online: user.is_online,
		lastSeen: user.last_seen_at ? timeAgo(user.last_seen_at) : undefined
	};
}
