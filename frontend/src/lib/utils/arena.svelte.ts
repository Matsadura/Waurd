import { getContext, setContext } from 'svelte';
import { BattleSocket, type HandGlyph, type ServerGlyph } from './battleSocket.svelte';

type ElementList = (HTMLElement | undefined)[];
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export const FEEL = {
	CardWidth: 'w-[18%] md:w-[11%] lg:w-[9%]',
	cardBottom: -12,
	spacing: 62,
	curvature: 3.2,
	rotation: 3.5,
	maxFan: 12,
	scale: 1.3,
	neighborPush: 70,
	glyphAspectRatio: '16 / 25',
	bounceDuration: 200, // time of bouncing of one glyph
	bounceStagger: 60 // time to wait between glyphs
};

export type activeView = 'slots' | 'perks' | 'draw' | 'discard';
export type WordSubmitPhase = 'idle' | 'checking' | 'invalid' | 'valid';

export class Arena {
	readonly slotCount = 8;

	battle = new BattleSocket();

	/* My glyphs and perks */
	glyphs = $derived<HandGlyph[]>(this.battle.state?.you.hand ?? []);
	drawPile = $derived<ServerGlyph[]>(this.battle.state?.you.draw_pile ?? []);
	discardPile = $derived<ServerGlyph[]>(this.battle.state?.you.discard_pile ?? []);
	slots = $state<(number | null)[]>(Array(this.slotCount).fill(null));
	hand = $derived<HandGlyph[]>(this.glyphs.filter((g) => !this.slots.includes(g.position)));

	overIndex = $state(-1); // index of the thing the glyph is over in current time (For now can be perk or word slot)

	#slotEls: ElementList = [];
	#perksEls: ElementList = [];

	/* Rendering */
	dragging = false;
	currentView: activeView = $state('slots');
	phase: WordSubmitPhase = $state('idle');

	/* Turn & clocks */
	turnNumber = $derived(this.battle.state?.turn ?? 0);
	turn = $derived.by<'me' | 'opponent' | null>(() => {
		if (this.battle.state === null ||
			this.battle.state.turn === 0 ||
			this.battle.state.winner !== null ||
			this.battle.aborted) {
			return null;
		} else {
			return this.battle.state.your_turn ? 'me' : 'opponent';
		}
	}
	);
	myTime = $derived(this.battle.state?.time_left?.you ?? 0);
	opponentTime = $derived(this.battle.state?.time_left?.opponent ?? 0);

	constructor() {
		// NOTE(Ali): This effects responsible for the countdown timer
		$effect(() => {
			if (this.turn !== null) {
				const interval = setInterval(() => {
					if (this.turn === 'me' && this.myTime > 0) {
						this.myTime = Math.max(0, this.myTime - 1);
					} else if (this.turn === 'opponent' && this.opponentTime > 0) {
						this.opponentTime = Math.max(0, this.opponentTime - 1);
					}
				}, 1000);

				return () => {
					clearInterval(interval);
				};
			}
		});

		// Reset placed slots whenever a new turn starts
		$effect(() => {
			this.turnNumber;
			this.slots = Array(this.slotCount).fill(null);
		});
	}

	async playWrongErrorAnimatino() { }

	constructSlotWord() {
		let word = '';
		this.slots.forEach((position) => {
			if (position !== null) {
				const glyph = this.glyph(position);
				if (glyph !== undefined) {
					word += glyph.letter;
				}
			}
		});
		return word;
	}

	async playSubmitAnimation() {
		if (this.phase === 'idle') {
			this.phase = 'checking';
			await sleep(1000);
			if (Math.random() > 0.5) {
				this.phase = 'valid';
			} else {
				this.phase = 'invalid';
			}
			await sleep(300);
			this.phase = 'idle';
			console.log(this.constructSlotWord());
		}
	}

	#register(list: ElementList, i: number) {
		return (el: HTMLElement) => {
			list[i] = el;
			return () => {
				if (list[i] === el) {
					list[i] = undefined;
				}
			};
		};
	}
	/** use as {@attach arena.slot(i)} */
	slotEl(i: number) {
		return this.#register(this.#slotEls, i);
	}

	/** use as {@attach arena.slot(i)} */
	perkEl(i: number) {
		return this.#register(this.#perksEls, i);
	}

	setDragging(isDragging: boolean) {
		this.dragging = isDragging;
	}

	/**
	 * Returns the data of a glyph in hand using its position
	 */
	glyph(position: number): HandGlyph | undefined {
		return this.glyphs.find((g) => g.position === position);
	}

	/**
	 * Put glyph at @slot index
	 */
	place(position: number, slot: number) {
		if (slot >= 0 && slot < this.slotCount) {
			this.remove(position);
			this.slots[slot] = position;
		}
	}

	/**
	 * Remove Glyph from slot
	 */
	remove(position: number) {
		const i = this.slots.indexOf(position);
		if (i >= 0) {
			this.slots[i] = null;
		}
	}

	/**
	 * Use when a glyph is clicked on
	 */
	toggle(position: number) {
		if (this.currentView === 'slots') {
			if (this.slots.includes(position)) {
				this.remove(position);
			} else {
				const emptySlot = this.slots.indexOf(null);
				if (emptySlot >= 0) {
					this.place(position, emptySlot);
				}
			}
		}
	}

	/**
	 * Should be called while moving card using mouse or finger?
	 */
	dragOver(x: number, y: number) {
		const elements = this.currentView === 'perks' ? this.#perksEls : this.#slotEls;

		let best = -1;
		let bestDist = Infinity;

		elements.forEach((el, i) => {
			if (el) {
				const r = el.getBoundingClientRect();
				const d = Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2));
				if (d < r.height * 0.9 && d < bestDist) {
					best = i;
					bestDist = d;
				}
			}
		});
		this.overIndex = best;
	}

	/**
	 * Should be called when the glyph is dropped, for example canceling while dragging
	 */
	drop(position: number) {
		if (this.currentView === 'slots') {
			if (this.overIndex >= 0) {
				this.place(position, this.overIndex);
			} else {
				this.remove(position);
			}
		} else if (this.currentView === 'perks') {
			console.log('You used perks number', this.overIndex);
		}
		this.overIndex = -1;
	}

	showPerksView() {
		this.currentView = 'perks';
		this.slots.fill(null);
	}

	setCurrentView(view: activeView) {
		this.currentView = view;
	}
}

const KEY = Symbol('arena');
export const setArena = () => setContext(KEY, new Arena());
export function getArena() {
	const arena = getContext<Arena | undefined>(KEY);
	if (!arena) {
		throw new Error('getArena() called while the its context was never initialized');
	}
	return arena;
}
