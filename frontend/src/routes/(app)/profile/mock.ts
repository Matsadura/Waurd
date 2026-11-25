// Fake data for the profile pages, so the UI can be built before the backend is wired.
// TODO: replace each export with a load function (+layout.server.ts / +page.server.ts).
import type { Achievement, Friend, Match, Perk } from '#lib/types/profile.ts';

// [opponent, opponentElo, result, eloChange, mode, turns, date]
const rows: [string, number, Match['result'], number, string, number, string][] = [
	['sakibbbb', 580, 'win', 14, '5 min', 10, 'Oct 6, 2026'],
	['darky', 625, 'loss', -11, '1 min', 16, 'Sep 19, 2026'],
	['assan', 601, 'win', 12, '10 min', 8, 'Sep 14, 2026'],
	['shadowfox', 590, 'win', 13, '5 min', 12, 'Sep 9, 2026'],
	['moonblade', 640, 'loss', -9, '5 min', 14, 'Sep 2, 2026'],
	['ember_k', 575, 'win', 15, '1 min', 9, 'Aug 28, 2026'],
	['vex', 610, 'win', 12, '10 min', 11, 'Aug 21, 2026'],
	['ravenwood', 655, 'loss', -8, '5 min', 18, 'Aug 15, 2026'],
	['sakibbbb', 570, 'win', 16, '5 min', 7, 'Aug 9, 2026'],
	['ironclad', 598, 'loss', -13, '1 min', 13, 'Aug 3, 2026'],
	['darky', 615, 'win', 14, '10 min', 15, 'Jul 27, 2026'],
	['assan', 585, 'win', 13, '5 min', 10, 'Jul 20, 2026'],
	['pale_knight', 620, 'loss', -10, '5 min', 17, 'Jul 12, 2026'],
	['ember_k', 560, 'win', 17, '1 min', 6, 'Jul 5, 2026']
];

export const matches: Match[] = rows.map(
	([opponent, opponentElo, result, eloChange, mode, turns, date], i) => ({
		id: i + 1,
		opponent,
		opponentElo,
		result,
		eloChange,
		mode,
		turns,
		date
	})
);

export const friends: Friend[] = [
	{ id: '1', username: 'sakibbbb', online: true },
	{ id: '2', username: 'darky', online: true },
	{ id: '3', username: 'assan', online: false, lastSeen: '2 hours ago' },
	{ id: '4', username: 'shadowfox', online: false, lastSeen: 'yesterday' },
	{ id: '5', username: 'moonblade', online: false, lastSeen: '3 days ago' },
	{ id: '6', username: 'ember_k', online: true }
];

export const incomingRequests: Friend[] = [
	{ id: '7', username: 'vex', online: true },
	{ id: '8', username: 'ravenwood', online: false, lastSeen: '5 hours ago' }
];

export const outgoingRequests: Friend[] = [{ id: '9', username: 'ironclad', online: false }];

export const achievements: Achievement[] = [
	{
		id: 'first-win',
		name: 'First Blood',
		description: 'Win your first duel.',
		xpReward: 100,
		progress: 1,
		target: 1,
		unlockedAt: 'Jul 5, 2026'
	},
	{
		id: 'wordsmith',
		name: 'Wordsmith',
		description: 'Cast a glyph chain of seven letters or more.',
		xpReward: 150,
		progress: 1,
		target: 1,
		unlockedAt: 'Jul 20, 2026',
		rewardPerk: 'Wordbreaker'
	},
	{
		id: 'streak-master',
		name: 'Unbroken',
		description: 'Win five duels in a row.',
		xpReward: 300,
		progress: 3,
		target: 5,
		rewardPerk: 'Blood for Blood'
	},
	{
		id: 'veteran',
		name: 'Veteran',
		description: 'Fight fifty duels.',
		xpReward: 250,
		progress: 14,
		target: 50
	},
	{
		id: 'fellowship',
		name: 'Fellowship',
		description: 'Befriend ten players.',
		xpReward: 120,
		progress: 6,
		target: 10
	},
	{
		id: 'champion',
		name: 'Champion',
		description: 'Reach 1100 elo.',
		xpReward: 500,
		progress: 606,
		target: 1100,
		rewardPerk: 'Crown of Ash'
	}
];

export const perkSlots = 3; // backend MAX_LOADOUT_SLOTS

export const perks: Perk[] = [
	{
		id: 'blood-for-blood',
		name: 'Blood for Blood',
		description: 'Transform this glyph into "RE" and raise its effect value by 5.',
		quote: "You miss 100% of the shots you didn't take",
		rarity: 'uncommon',
		target: 'Any',
		durability: 4,
		owned: true
	},
	{
		id: 'wordbreaker',
		name: 'Wordbreaker',
		description: 'Double the effect value of a Power glyph.',
		quote: 'Words are weapons.',
		rarity: 'rare',
		target: 'Power',
		durability: 3,
		owned: true
	},
	{
		id: 'iron-skin',
		name: 'Iron Skin',
		description: 'Turn a Power glyph into a Skill glyph.',
		rarity: 'common',
		target: 'Power',
		durability: 6,
		owned: true
	},
	{
		id: 'last-breath',
		name: 'Last Breath',
		description: 'Gain x2 if the glyph ends the word.',
		quote: 'The last letter cuts deepest.',
		rarity: 'uncommon',
		target: 'Skill',
		durability: 5,
		owned: true
	},
	{
		id: 'crown-of-ash',
		name: 'Crown of Ash',
		description: 'Halve the cost of every glyph in your hand for one turn.',
		quote: 'Only embers remain.',
		rarity: 'legendary',
		target: 'Any',
		owned: false
	},
	{
		id: 'hollow-echo',
		name: 'Hollow Echo',
		description: 'Erase one glyph from your deck for good.',
		rarity: 'rare',
		target: 'Any',
		durability: 2,
		owned: false
	}
];

// Placeholder titles, the team should decide the real thresholds.
const ranks: [number, string][] = [
	[0, 'change-me'],
	[500, 'change-me'],
	[800, 'change-me'],
	[1100, 'change-me'],
	[1400, 'change-me'],
	[1700, 'change-me']
];

const wins = matches.filter((match) => match.result === 'win').length;

export const player = {
	username: 'kirito_19',
	joined: 'Nov 10, 2024',
	friends: friends.length,
	online: true,
	level: 12,
	xp: 650,
	nextLevelXp: 1000,
	elo: 606,
	games: matches.length,
	wins
};

export const rank = [...ranks].reverse().find(([min]) => player.elo >= min)![1];
