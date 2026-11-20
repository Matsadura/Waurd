// Shapes of the match socket's messages (see the API spec's WebSockets tab).

export type Effect = 'DAMAGE' | 'DEFENSE' | 'HEAL' | 'WEAK' | 'VULNERABLE';

export type Glyph = {
	id: string;
	letters: string;
	type: 'POWER' | 'SKILL';
	effect: Effect;
	value: number;
	conditional_slot: string | null;
};

export type Status = { effect: 'WEAK' | 'VULNERABLE'; turns_left: number; applied_turn: number };

export type PlayerView = {
	id: string;
	hp: number;
	defense: number;
	statuses: Status[];
	draw_count: number;
	discard_count: number;
	hand_size: number;
	ready: boolean;
};

export type OwnedPerk = { instance_id: string; perk_id: string; durability: number | null };

export type Snapshot = {
	turn: number;
	phase: 'WAITING' | 'ACTION' | 'DRAFT' | 'ENDED';
	max_hp: number;
	active_player_id: string;
	players: PlayerView[];
	hand: Glyph[] | null;
	draft_offer: string[] | null;
	perks: OwnedPerk[];
	rerolls_left: number;
	clocks: Record<string, number>;
	clock_running_for: string | null;
	winner_id: string | null;
	end_reason: string | null;
};

export type Change = { stage: string; before: number; after: number; perk_id: string | null };

export type Step = {
	glyph_id: string;
	letters: string;
	type: 'POWER' | 'SKILL';
	effect: Effect;
	value: number;
	changes: Change[];
	final_value: number;
};

export type Resolution = {
	turn: number;
	player_id: string;
	word: string;
	steps: Step[];
	totals: { damage: number; defense: number; heal: number };
	damage_blocked: number;
	hp_damage: number;
	hp_healed: number;
	statuses_applied: Status[];
	target_defeated: boolean;
};

export type Perk = {
	id: string;
	name: string;
	rarity: 'COMMON' | 'UNCOMMON' | 'RARE' | 'LEGENDARY';
	description: string;
	quote: string | null;
	target_glyph_type: 'POWER' | 'SKILL' | 'ANY';
	durability: number | null;
};

export type DraftOption = {
	perk_id: string;
	name: string;
	rarity: Perk['rarity'];
	description: string;
	durability: number | null;
};

export type Draft = { options: DraftOption[]; pick_count: number; rerolls_left: number };

export type Ended = {
	winner_id: string;
	end_reason: string;
	elo_delta: Record<string, number>;
};

export type Message = { type: string; data: Record<string, unknown>; seq?: number };
