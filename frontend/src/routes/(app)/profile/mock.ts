// Fake data for Perks
import type { Perk } from '#lib/types/profile.ts';

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
