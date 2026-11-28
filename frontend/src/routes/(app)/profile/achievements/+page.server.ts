import { error, redirect } from '@sveltejs/kit';
import { api } from '#lib/server/api.ts';
import type { Achievement } from '#lib/types/profile.ts';
import type { PageServerLoad } from './$types';

type AchievementResponse = {
	id: string;
	name: string;
	description: string;
	icon_url: string;
	xp_reward: number;
	target_value: number;
	reward_perk: { name: string } | null;
};

type UserAchievementResponse = {
	achievement_id: string;
	current_progress: number;
	is_completed: boolean;
	unlocked_at: string | null;
};

export const load: PageServerLoad = async ({ fetch }) => {
	let catalogResponse: Response;
	let progressResponse: Response;

	try {
		[catalogResponse, progressResponse] = await Promise.all([
			fetch(api('/achievements?page=1&size=100')),
			fetch(api('/users/me/achievements'))
		]);
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (catalogResponse.status === 401 || progressResponse.status === 401) {
		redirect(303, '/login');
	}

	if (!catalogResponse.ok || !progressResponse.ok) {
		error(502, 'Could not retrieve your achievements.');
	}

	const catalog: { items: AchievementResponse[] } = await catalogResponse.json();
	const progress: UserAchievementResponse[] = await progressResponse.json();

	const progressById = new Map(progress.map((item) => [item.achievement_id, item]));

	const achievements: Achievement[] = catalog.items.map((achievement) => {
		const userProgress = progressById.get(achievement.id);

		return {
			id: achievement.id,
			name: achievement.name,
			description: achievement.description,
			iconUrl: achievement.icon_url || undefined,
			xpReward: achievement.xp_reward,
			target: achievement.target_value,
			progress: userProgress?.current_progress ?? 0,
			unlockedAt:
				userProgress?.is_completed && userProgress.unlocked_at
					? new Date(userProgress.unlocked_at).toLocaleDateString('en-US', {
							month: 'short',
							day: 'numeric',
							year: 'numeric'
						})
					: undefined,
			rewardPerk: achievement.reward_perk?.name
		};
	});

	return { achievements };
};
