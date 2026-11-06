// arena.svelte.ts
import { getContext, setContext } from 'svelte';

export type Glyph = { id: string; letter: string };

export const FEEL = {
	cardBottom: -12,
	spacing: 62,
	curvature: 3.2,
	rotation: 3.5,
	maxFan: 12,
	scale: 1.3,
	neighborPush: 70,
	glyphAspectRatio: '16 / 25'
};

export class Arena {
	readonly slotCount = 8;

	glyphs = $state<Glyph[]>([...'ALIJBAEIISM1'].map((letter, i) => ({ id: `g${i}`, letter })));
	slots = $state<(string | null)[]>(Array(this.slotCount).fill(null));
	hand = $derived(this.glyphs.filter((g) => !this.slots.includes(g.id)));

	overSlot = $state(-1);

	#slotEls: (HTMLElement | undefined)[] = [];

	/** use as {@attach arena.slot(i)} */
	slot(i: number) {
		return (el: HTMLElement) => {
			this.#slotEls[i] = el;
			return () => (this.#slotEls[i] = undefined);
		};
	}

	/**
	 * Returns the data of a glyph using its id
	 */
	glyph(id: string): Glyph | null {
		const glyphData = this.glyphs.find((g) => g.id === id);
		return glyphData || null;
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
		if (i >= 0) this.slots[i] = null;
	}

	/**
	 * Should be when tab event is fired at draggable element
	 */
	toggle(id: string) {
		if (this.slots.includes(id)) this.remove(id);
		else this.place(id, this.slots.indexOf(null));
	}

	/**
	 * Should be called while moving card using pointer
	 */
	dragOver(x: number, y: number) {
		// console.log(x, y);
		let best = -1,
			bestDist = Infinity;
		console.log($state.snapshot( this.#slotEls));
		this.#slotEls.forEach((el, i) => {
			if (!el) return;
			const r = el.getBoundingClientRect();
			const d = Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2));
			if (d < r.height * 0.9 && d < bestDist) [best, bestDist] = [i, d];
		});
		this.overSlot = best;
	}

	/**
	 * Should be called when the glyph is dropeed, for example calling up while dragging
	 */
	drop(id: string) {
		if (this.overSlot >= 0) this.place(id, this.overSlot);
		else this.remove(id);
		this.overSlot = -1;
	}
}

const KEY = Symbol('arena');
export const setArena = () => setContext(KEY, new Arena());
export function getArena() {
	const arena = getContext<Arena | undefined>(KEY);
	if (!arena) throw new Error('getArena() called while the its context was never initialized');
	return arena;
}
