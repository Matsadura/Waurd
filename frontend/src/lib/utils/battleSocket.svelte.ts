import { PUBLIC_BACKEND_URL } from '$app/env/public';

export type GlyphType = 'power' | 'skill';
export type GlyphEffectType = 'damage' | 'heal' | 'defense' | 'vulnerable' | 'weak';
export type EndReason = 'HEALTH_DEPLETED' | 'RESIGNATION' | 'DISCONNECT' | 'TIMEOUT';
export type PerkRarity = 'common' | 'uncommon' | 'rare' | 'legendary';
export type PerkTarget = 'damage' | 'heal_defense' | 'any';

export type ServerGlyph = {
	letter: string;
	type: GlyphType;
	effect_type: GlyphEffectType;
	effect_value: number;
	bonus?: string | null;
};

export type HandGlyph = ServerGlyph & {
	position: number;
};

export type ServerPerk = {
	perk_id: string;
	name: string;
	rarity: PerkRarity;
	description: string;
	target: PerkTarget;
	durability: number | null;
};

export type OwnedPerk = ServerPerk & {
	instance_id: number;
	durability_left: number | null;
};

export type PerkDraft = {
	options: ServerPerk[];
	rerolls_left: number;
};

export type BattleState = {
	type: 'STATE';
	turn: number;
	your_turn: boolean;
	winner: number | null;
	you_won: boolean | null;
	end_reason: EndReason | null;
	you: {
		hp: number;
		hand: HandGlyph[];
		draw_pile?: ServerGlyph[];
		discard_pile?: ServerGlyph[];
		defense?: number;
		statuses?: Record<string, number>;
		perks?: OwnedPerk[];
		draft?: PerkDraft | null;
	};
	opponent: {
		hp: number;
		hand_size: number;
		draw_pile_size?: number;
		discard_pile_size?: number;
		defense?: number;
		statuses?: Record<string, number>;
		perk_count?: number;
	};
	time_left?: {
		you: number;
		opponent: number;
	};
	log?: string[];
};

export type ServerMessage =
	| BattleState
	| { type: 'ACTION_REJECTED'; reason: string }
	| { type: 'OPPONENT_DISCONNECTED'; grace_seconds: number }
	| { type: 'OPPONENT_RECONNECTED' }
	| { type: 'MATCH_ABORTED' };

export type ClientMessage =
	| { type: 'CAST_WORD'; positions: number[] }
	| { type: 'APPLY_PERK'; perk_instance_id: number; position: number }
	| { type: 'REROLL_PERKS' }
	| { type: 'SELECT_PERKS'; perk_ids: string[] }
	| { type: 'PASS_TURN' }
	| { type: 'RESIGN' };

export type ConnectionStatus = 'connecting' | 'connected' | 'closed';

export class BattleSocket {
	status = $state<ConnectionStatus>('connecting');
	state = $state<BattleState | null>(null);
	error = $state<string | null>(null);
	aborted = $state(false);
	opponentGraceSeconds = $state<number | null>(null);

	#socket: WebSocket | null = null;

	connect(battleId: string) {
		// NOTE(Ali): this function runs inside $effect, so make sure no state is readed.
		const wsBase = PUBLIC_BACKEND_URL.replace(/^http/, 'ws');
		const socket = new WebSocket(`${wsBase}/ws/matches/${battleId}`);

		this.#socket = socket;
		this.status = 'connecting';
		this.state = null;
		this.error = null;
		this.aborted = false;
		this.opponentGraceSeconds = null;

		socket.onopen = () => {
			this.status = 'connected';
			this.error = null;
		};

		socket.onmessage = (event) => {
			let message: ServerMessage | null = null;

			try {
				message = JSON.parse(event.data) as ServerMessage;
			} catch {
				this.error = 'Received unreadable message from server.';
			}

			if (message !== null) {
				if (message.type === 'STATE') {
					this.state = message;
					this.error = null;
				} else if (message.type === 'ACTION_REJECTED') {
					this.error = message.reason;
				} else if (message.type === 'OPPONENT_DISCONNECTED') {
					this.opponentGraceSeconds = message.grace_seconds;
				} else if (message.type === 'OPPONENT_RECONNECTED') {
					this.opponentGraceSeconds = null;
				} else if (message.type === 'MATCH_ABORTED') {
					this.aborted = true;
				} else {
					this.error = 'Received unknown message from server.';
				}
			}
		};

		socket.onerror = () => {
			this.error = 'WebSocket connection error.';
		};

		socket.onclose = (event) => {
			this.status = 'closed';
			this.#socket = null;

			if (event.code !== 1000 && !this.aborted) {
				if (this.state === null) {
					this.error = `Could not connect to battle (code ${event.code}).`;
				} else if (this.state.winner === null) {
					this.error = `Connection closed (code ${event.code}).`;
				}
			}
		};

		return () => {
			socket.onopen = null;
			socket.onmessage = null;
			socket.onerror = null;
			socket.onclose = null;
			socket.close(1000);
			this.#socket = null;
		};
	}

	send(message: ClientMessage) {
		if (this.#socket === null || this.#socket.readyState !== WebSocket.OPEN) {
			this.error = 'Cannot send action: not connected.';
		} else {
			this.#socket.send(JSON.stringify(message));
		}
	}
}
