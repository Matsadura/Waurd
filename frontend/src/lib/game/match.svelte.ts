// One match's socket: keeps the latest snapshot and what just happened.
import { socketUrl } from '#lib/api.ts';
import type { Draft, Ended, Message, Perk, Resolution, Snapshot } from './types';

export type LogEntry = { id: number; text: string; tone: 'info' | 'good' | 'bad' };

export class MatchConnection {
	snapshot = $state<Snapshot | null>(null);
	// performance.now() when the snapshot arrived, to run the active clock locally.
	snapshotAt = $state(0);
	lastWord = $state<Resolution | null>(null);
	draft = $state<Draft | null>(null);
	ended = $state<Ended | null>(null);
	rejection = $state('');
	opponentAway = $state<number | null>(null);
	connected = $state(false);
	closedReason = $state('');
	log = $state<LogEntry[]>([]);

	private socket: WebSocket | null = null;
	// PLAYER_READY goes once per connection: a second snapshot can arrive before
	// the server has handled the first one.
	private readySent = false;
	private stopped = false;
	private logId = 0;

	constructor(
		readonly matchId: string,
		readonly me: string,
		private readonly nameOf: (userId: string) => string,
		private readonly perks: () => Map<string, Perk>
	) {}

	get isMyTurn(): boolean {
		return this.snapshot?.active_player_id === this.me && this.snapshot.phase !== 'ENDED';
	}

	open(): void {
		this.stopped = false;
		const socket = new WebSocket(socketUrl(`/ws/matches/${this.matchId}`));
		this.socket = socket;
		socket.onopen = () => {
			this.readySent = false;
			this.connected = true;
			this.closedReason = '';
		};
		socket.onmessage = (event) => this.handle(JSON.parse(event.data) as Message);
		socket.onclose = (event) => {
			this.connected = false;
			if (event.code === 1008) {
				this.closedReason = event.reason || 'You can’t join this match.';
				this.stopped = true;
			}
			if (!this.stopped && !this.ended) setTimeout(() => this.open(), 1500);
		};
	}

	close(): void {
		this.stopped = true;
		this.socket?.close();
	}

	send(type: string, data: Record<string, unknown> = {}): void {
		this.rejection = '';
		this.socket?.send(JSON.stringify({ type, data }));
	}

	private note(text: string, tone: LogEntry['tone'] = 'info'): void {
		this.log = [{ id: ++this.logId, text, tone }, ...this.log].slice(0, 30);
	}

	private handle(message: Message): void {
		const data = message.data as never;
		switch (message.type) {
			case 'MATCH_STATE': {
				const snapshot = data as Snapshot;
				this.snapshot = snapshot;
				this.snapshotAt = performance.now();
				const mine = snapshot.players.find((p) => p.id === this.me);
				if (snapshot.phase === 'WAITING' && mine && !mine.ready && !this.readySent) {
					this.readySent = true;
					this.send('PLAYER_READY');
				}
				if (snapshot.phase !== 'DRAFT' || snapshot.active_player_id !== this.me) {
					this.draft = null;
				} else if (!this.draft && snapshot.draft_offer) {
					// Reconnected mid-draft: rebuild the options from the catalog.
					const catalog = this.perks();
					this.draft = {
						options: snapshot.draft_offer.map((id) => {
							const perk = catalog.get(id);
							return {
								perk_id: id,
								name: perk?.name ?? id,
								rarity: perk?.rarity ?? 'COMMON',
								description: perk?.description ?? '',
								durability: perk?.durability ?? null
							};
						}),
						pick_count: Math.min(1, snapshot.draft_offer.length),
						rerolls_left: snapshot.rerolls_left
					};
				}
				if (snapshot.phase === 'ENDED' && !this.ended && snapshot.winner_id) {
					this.ended = {
						winner_id: snapshot.winner_id,
						end_reason: snapshot.end_reason ?? '',
						elo_delta: {}
					};
				}
				break;
			}
			case 'MATCH_START':
				this.note('The match has started.', 'good');
				break;
			case 'TURN_START':
				this.note('Your turn.', 'good');
				break;
			case 'OPPONENT_TURN_START':
				this.note(
					`${this.nameOf((data as { active_player_id: string }).active_player_id)}'s turn.`
				);
				break;
			case 'WORD_RESOLVED': {
				const word = data as Resolution;
				this.lastWord = word;
				const who = word.player_id === this.me ? 'You' : this.nameOf(word.player_id);
				const parts = [];
				if (word.totals.damage) parts.push(`${word.hp_damage} damage`);
				if (word.damage_blocked) parts.push(`${word.damage_blocked} blocked`);
				if (word.totals.defense) parts.push(`+${word.totals.defense} Defense`);
				if (word.hp_healed) parts.push(`+${word.hp_healed} HP`);
				for (const status of word.statuses_applied)
					parts.push(status.effect === 'WEAK' ? 'Weak' : 'Vulnerable');
				this.note(
					`${who} cast ${word.word}: ${parts.join(', ') || 'no effect'}.`,
					word.player_id === this.me ? 'good' : 'bad'
				);
				break;
			}
			case 'TURN_PASSED': {
				const who = (data as { player_id: string }).player_id;
				this.note(`${who === this.me ? 'You' : this.nameOf(who)} passed.`);
				break;
			}
			case 'PERK_APPLIED': {
				const result = data as { perk_id: string; applied: boolean; destroyed: boolean };
				const name = this.perks().get(result.perk_id)?.name ?? result.perk_id;
				this.note(
					result.applied
						? `${name} applied${result.destroyed ? ' (used up)' : ''}.`
						: `${name} had no effect.`,
					result.applied ? 'good' : 'info'
				);
				break;
			}
			case 'PERK_DRAFT_OPTIONS': {
				const draft = data as {
					options: Draft['options'];
					pick_count: number;
					rerolls_left: number;
				};
				this.draft = {
					options: draft.options,
					pick_count: draft.pick_count,
					rerolls_left: draft.rerolls_left
				};
				break;
			}
			case 'ACTION_REJECTED':
				this.rejection = (data as { reason: string }).reason;
				break;
			case 'ERROR':
				this.rejection = (data as { detail: string }).detail;
				break;
			case 'OPPONENT_DISCONNECTED':
				this.opponentAway = (data as { grace_seconds: number }).grace_seconds;
				this.note('Your opponent disconnected.', 'bad');
				break;
			case 'OPPONENT_RECONNECTED':
				this.opponentAway = null;
				this.note('Your opponent is back.');
				break;
			case 'MATCH_ENDED':
				this.ended = data as Ended;
				this.opponentAway = null;
				this.draft = null;
				break;
		}
	}
}

export const END_REASONS: Record<string, string> = {
	HEALTH_DEPLETED: 'HP ran out',
	TIMEOUT: 'The clock ran out',
	RESIGNATION: 'Resigned',
	DISCONNECT: 'Didn’t come back in time'
};
