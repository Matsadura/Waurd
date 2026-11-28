// Shapes of the data shown on the profile pages. They follow the backend schemas
// (MatchResponse, FriendUserResponse, UserAchievementResponse, PerkResponse), in camelCase.

export type MatchResult = 'win' | 'loss' | 'draw'; // // TODO: Confirm whether draws will be supported by the game.

export type Match = {
	id: string | number;
	opponent: string;
	opponentElo: number | null;
	result: MatchResult;
	eloChange: number | null;
	mode: string;
	turns: number | null;
	date: string;
};

export type Friend = {
	id: string;
	username: string;
	avatarUrl?: string;
	online: boolean;
	lastSeen?: string; // already formatted, like "2 hours ago"
};

export type Achievement = {
	id: string;
	name: string;
	description: string;
	iconUrl?: string;
	xpReward: number;
	progress: number;
	target: number;
	completed: boolean;
	unlockedAt?: string; // set once completed
	rewardPerk?: string; // name of the perk it unlocks
};

export type Rarity = 'common' | 'uncommon' | 'rare' | 'legendary';

export type Perk = {
	id: string;
	name: string;
	description: string;
	quote?: string;
	rarity: Rarity;
	target: 'Power' | 'Skill' | 'Any';
	durability?: number; // missing means it never breaks
	owned: boolean;
};
