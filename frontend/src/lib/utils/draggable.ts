// draggable.ts
import type { Attachment } from 'svelte/attachments';

export default function draggable(
	onMove: (x: number, y: number) => void = (x, y) => {},
	onDrop: () => void = () => {},
	onTap: () => void = () => {},
	threshold = 10
): Attachment<HTMLElement> {
	return (el) => {
		let id = -1,
			sx = 0,
			sy = 0,
			moved = false;

		const down = (e: PointerEvent) => {
			if (id !== -1 || !e.isPrimary || (e.pointerType === 'mouse' && e.button !== 0)) return;
			id = e.pointerId;
			sx = e.clientX;
			sy = e.clientY;
			moved = false;
			el.setPointerCapture(id);
		};

		const move = (e: PointerEvent) => {
			if (e.pointerId !== id) return;
			const dx = e.clientX - sx,
				dy = e.clientY - sy;
			if (!moved && Math.hypot(dx, dy) < threshold) return;
			moved = true;
			el.dataset.dragging = '';
			el.style.setProperty('--dx', `${dx}px`);
			el.style.setProperty('--dy', `${dy}px`);
			onMove(e.clientX, e.clientY);
		};

		const up = (e: PointerEvent) => {
			if (e.pointerId !== id) return;
			id = -1;
			delete el.dataset.dragging;
			el.style.removeProperty('--dx');
			el.style.removeProperty('--dy');
			if (moved) onDrop();
		};

		const click = () => {
			if (!moved) onTap();
		};

		el.addEventListener('pointerdown', down);
		el.addEventListener('pointermove', move);
		el.addEventListener('pointerup', up);
		el.addEventListener('pointercancel', up);
		el.addEventListener('lostpointercapture', up);
		el.addEventListener('click', click);

		return () => {
			el.removeEventListener('pointerdown', down);
			el.removeEventListener('pointermove', move);
			el.removeEventListener('pointerup', up);
			el.removeEventListener('pointercancel', up);
			el.removeEventListener('lostpointercapture', up);
			el.removeEventListener('click', click);
		};
	};
}

export function pointInsideDOMRect(pointX: number, pointY: number, rect: DOMRect) {
	return pointX >= rect.x && pointX < rect.right && pointY >= rect.y && pointY < rect.bottom;
}
