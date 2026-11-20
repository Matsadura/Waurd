// The match socket client: what it does with each server message.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchConnection } from './match.svelte.ts';
import type { Perk, Snapshot } from './types.ts';

class FakeSocket {
	static last: FakeSocket;
	sent: { type: string; data: Record<string, unknown> }[] = [];
	onopen: (() => void) | null = null;
	onmessage: ((event: { data: string }) => void) | null = null;
	onclose: ((event: { code: number; reason: string }) => void) | null = null;
	constructor(readonly url: string) {
		FakeSocket.last = this;
	}
	send(text: string) {
		this.sent.push(JSON.parse(text));
	}
	close() {}
	// Test helpers
	open() {
		this.onopen?.();
	}
	server(type: string, data: object) {
		this.onmessage?.({ data: JSON.stringify({ type, data, seq: 1 }) });
	}
}

const ME = 'me';
const THEM = 'them';
const catalog = new Map<string, Perk>([
	[
		'amplify',
		{
			id: 'amplify',
			name: 'Amplify',
			rarity: 'RARE',
			description: 'Raise this glyph’s value by half.',
			quote: null,
			target_glyph_type: 'POWER',
			durability: 3
		}
	]
]);

function snapshot(overrides: Partial<Snapshot> = {}): Snapshot {
	return {
		turn: 1,
		phase: 'ACTION',
		max_hp: 130,
		active_player_id: ME,
		players: [
			{
				id: ME,
				hp: 130,
				defense: 0,
				statuses: [],
				draw_count: 33,
				discard_count: 0,
				hand_size: 7,
				ready: true
			},
			{
				id: THEM,
				hp: 130,
				defense: 35,
				statuses: [],
				draw_count: 40,
				discard_count: 0,
				hand_size: 0,
				ready: true
			}
		],
		hand: [],
		draft_offer: null,
		perks: [],
		rerolls_left: 3,
		clocks: { [ME]: 300000, [THEM]: 300000 },
		clock_running_for: ME,
		winner_id: null,
		end_reason: null,
		...overrides
	};
}

function waiting(ready: boolean): Snapshot {
	const s = snapshot({ phase: 'WAITING', turn: 0 });
	s.players[0].ready = ready;
	s.players[1].ready = false;
	return s;
}

let match: MatchConnection;
let socket: FakeSocket;

beforeEach(() => {
	vi.stubGlobal('WebSocket', FakeSocket);
	vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:5173' });
	vi.useFakeTimers();
	match = new MatchConnection(
		'm-1',
		ME,
		(id) => (id === THEM ? 'Bob' : id),
		() => catalog
	);
	match.open();
	socket = FakeSocket.last;
	socket.open();
});

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('connecting', () => {
	it('opens the match socket through the API path', () => {
		expect(socket.url).toBe('ws://localhost:5173/api/v1/ws/matches/m-1');
		expect(match.connected).toBe(true);
	});

	it('says it is ready once, even if a second waiting snapshot comes first', () => {
		socket.server('MATCH_STATE', waiting(false));
		socket.server('MATCH_STATE', waiting(false));

		expect(socket.sent.filter((m) => m.type === 'PLAYER_READY')).toHaveLength(1);
	});

	it('says it is ready again after reconnecting', () => {
		socket.server('MATCH_STATE', waiting(false));
		socket.onclose?.({ code: 1006, reason: '' });
		vi.advanceTimersByTime(1500);
		const second = FakeSocket.last;
		second.open();
		second.server('MATCH_STATE', waiting(false));

		expect(second).not.toBe(socket);
		expect(second.sent.map((m) => m.type)).toEqual(['PLAYER_READY']);
	});

	it('stops when the server refuses the match', () => {
		socket.onclose?.({ code: 1008, reason: 'You are not a player in this match' });
		vi.advanceTimersByTime(5000);

		expect(match.closedReason).toBe('You are not a player in this match');
		expect(FakeSocket.last).toBe(socket);
	});
});

describe('playing', () => {
	it('keeps the latest snapshot and knows whose turn it is', () => {
		socket.server('MATCH_STATE', snapshot());
		expect(match.isMyTurn).toBe(true);

		socket.server('MATCH_STATE', snapshot({ active_player_id: THEM }));
		expect(match.isMyTurn).toBe(false);
	});

	it('logs a resolved word and keeps it for the breakdown', () => {
		socket.server('WORD_RESOLVED', {
			turn: 1,
			player_id: THEM,
			word: 'CAB',
			steps: [],
			totals: { damage: 32, defense: 0, heal: 10 },
			damage_blocked: 5,
			hp_damage: 27,
			hp_healed: 10,
			statuses_applied: [{ effect: 'WEAK', turns_left: 2, applied_turn: 1 }],
			target_defeated: false
		});

		expect(match.lastWord?.word).toBe('CAB');
		expect(match.log[0].text).toBe('Bob cast CAB: 27 damage, 5 blocked, +10 HP, Weak.');
		expect(match.log[0].tone).toBe('bad');
	});

	it('shows a rejection until the next move', () => {
		socket.server('ACTION_REJECTED', {
			action: 'CAST_WORD',
			turn: 1,
			code: 'UNKNOWN_WORD',
			reason: 'XQ is not a valid word.'
		});
		expect(match.rejection).toBe('XQ is not a valid word.');

		match.send('PASS_TURN', { turn: 1 });
		expect(match.rejection).toBe('');
		expect(socket.sent.at(-1)).toEqual({ type: 'PASS_TURN', data: { turn: 1 } });
	});
});

describe('drafting', () => {
	it('opens the draft and closes it when the turn moves on', () => {
		socket.server('PERK_DRAFT_OPTIONS', {
			turn: 1,
			options: [
				{ perk_id: 'amplify', name: 'Amplify', rarity: 'RARE', description: '', durability: 3 }
			],
			pick_count: 1,
			rerolls_left: 3
		});
		expect(match.draft?.options).toHaveLength(1);

		socket.server('MATCH_STATE', snapshot({ turn: 2, active_player_id: THEM }));
		expect(match.draft).toBeNull();
	});

	it('rebuilds an open draft from the catalog after a reconnect', () => {
		socket.server(
			'MATCH_STATE',
			snapshot({ phase: 'DRAFT', draft_offer: ['amplify'], rerolls_left: 2 })
		);

		expect(match.draft).toEqual({
			options: [
				{
					perk_id: 'amplify',
					name: 'Amplify',
					rarity: 'RARE',
					description: 'Raise this glyph’s value by half.',
					durability: 3
				}
			],
			pick_count: 1,
			rerolls_left: 2
		});
	});
});

describe('the end', () => {
	it('keeps the result with the rating change', () => {
		socket.server('MATCH_ENDED', {
			winner_id: ME,
			end_reason: 'HEALTH_DEPLETED',
			elo_delta: { [ME]: 16, [THEM]: -16 }
		});

		expect(match.ended?.winner_id).toBe(ME);
		expect(match.ended?.elo_delta[ME]).toBe(16);
	});

	it('shows the result when joining a match that already ended', () => {
		socket.server(
			'MATCH_STATE',
			snapshot({ phase: 'ENDED', winner_id: THEM, end_reason: 'TIMEOUT' })
		);

		expect(match.ended).toEqual({ winner_id: THEM, end_reason: 'TIMEOUT', elo_delta: {} });
	});

	it('tracks an opponent who drops and comes back', () => {
		socket.server('OPPONENT_DISCONNECTED', { grace_seconds: 30 });
		expect(match.opponentAway).toBe(30);

		socket.server('OPPONENT_RECONNECTED', {});
		expect(match.opponentAway).toBeNull();
	});
});
