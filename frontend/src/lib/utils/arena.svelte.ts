import { getContext, setContext } from 'svelte';

export type Glyph = { id: string; letter: string };
type ElementList = (HTMLElement | undefined)[];
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export const FEEL = {
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

	glyphs = $state<Record<string, Glyph>>(
		Object.fromEntries(
			[...'ABCDEFYGHIGKL', 'ER'].map((letter, i) => [`g${i}`, { id: `g${i}`, letter }])
		)
	);
	drawPile = $state<Record<string, Glyph>>(
		Object.fromEntries([...'ABCDEFYGHIJ!L'].map((letter, i) => [`g${i}`, { id: `g${i}`, letter }]))
	);
	discardPile = $state<Record<string, Glyph>>(
		Object.fromEntries([...'ABCDEFYGHIJ!L'].map((letter, i) => [`g${i}`, { id: `g${i}`, letter }]))
	);
	slots = $state<(string | null)[]>(Array(this.slotCount).fill(null));
	hand = $derived(Object.keys(this.glyphs).filter((g) => !this.slots.includes(g)));

	overIndex = $state(-1); // index of the thing the glyph is over in current time

	#slotEls: ElementList = [];
	#perksEls: ElementList = [];

	dragging = false;
	currentView: activeView = $state('slots');

	phase: WordSubmitPhase = $state('idle');

	async playWrongErrorAnimatino() {}

	constructSlotWord() {
		let word: string = '';
		this.slots.forEach((id) => {
			if (id) word += this.glyph(id).letter;
		});
		return word;
	}

	async playSubmitAnimation() {
		const count = this.slots.filter(Boolean).length;
		if (this.phase !== 'idle') return;

		// const r = await fetch(`http://localhost:8001/check?word=${this.constructSlotWord()}`).catch(
		// 	console.log
		// );
		// await new Promise((r) => setTimeout(r, FEEL.bounceDuration + (count - 1) * FEEL.bounceStagger));
		// this.isBouncing = false;

		// const json = await r?.json();

		// console.log(json);'
		this.phase = 'checking';
		await sleep(1000);
		if (Math.random() > 0.5) {
			// if (false) {
			this.phase = 'valid';
		} else {
			this.phase = 'invalid';
		}
		await sleep(300);
		this.phase = 'idle';
	}

	#register(list: ElementList, i: number) {
		return (el: HTMLElement) => {
			list[i] = el;
			return () => {
				if (list[i] === el) list[i] = undefined;
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
	 * Returns the data of a glyph using its id
	 */
	glyph(id: string): Glyph {
		const glyph = this.glyphs[id];
		if (!glyph) {
			throw new Error(`Unknown glyph: ${id}`);
		}
		return this.glyphs[id];
	}

	/**
	 * Put glyph at @slot index
	 */
	place(id: string, slot: number) {
		if (slot < 0 || slot >= this.slotCount) return;
		this.remove(id);
		this.slots[slot] = id;
	}

	/**
	 * Remove Glyph from slot
	 */
	remove(id: string) {
		const i = this.slots.indexOf(id);
		if (i >= 0) {
			this.slots[i] = null;
		}
	}

	/**
	 * Use when a glyph is clicked on
	 */
	toggle(id: string) {
		if (this.currentView === 'slots') {
			if (this.slots.includes(id)) {
				this.remove(id);
			} else {
				this.place(id, this.slots.indexOf(null));
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
			if (!el) return;
			const r = el.getBoundingClientRect();
			const d = Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2));
			if (d < r.height * 0.9 && d < bestDist) [best, bestDist] = [i, d];
		});
		this.overIndex = best;
	}

	/**
	 * Should be called when the glyph is dropeed, for example canceling while dragging
	 */
	drop(id: string) {
		if (this.currentView === 'slots') {
			if (this.overIndex >= 0) {
				this.place(id, this.overIndex);
			} else {
				this.remove(id);
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
