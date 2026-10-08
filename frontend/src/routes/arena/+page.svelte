<script lang="ts">
	let x = $state(0);
	let y = $state(0);
	let GlyphState = $state('idle');

	let pointerId: Number = -1;
	let startPointerX = 0;
	let startPointerY = 0;
	let startX = 0;
	let startY = 0;

	function startDrag(event: PointerEvent) {
		if (event.isPrimary && event.button === 0 && GlyphState === 'idle') {
			event.preventDefault();

			pointerId = event.pointerId;

			startPointerX = event.clientX;
			startPointerY = event.clientY;

			startX = x;
			startY = y;

			const element = event.currentTarget;

			if (element instanceof HTMLElement) {
				element.setPointerCapture(event.pointerId);
				GlyphState = 'dragging';
				updateTarget(event.clientX, event.clientY);
			}
		}
	}

	function moveDrag(event: PointerEvent) {
		if (GlyphState === 'dragging' && event.pointerId === pointerId) {
			let dx = event.clientX - startPointerX;
			let dy = event.clientY - startPointerY;

			x = startX + dx;
			y = startY + dy;
			updateTarget(event.clientX, event.clientY);
		}
	}

	function endDrag(event: PointerEvent) {
		if (event.pointerId === pointerId) {
			moveDrag(event);

			GlyphState = 'idle';
			pointerId = -1;
		}
	}

	function cancelDrag(event: PointerEvent) {
		if (event.pointerId === pointerId) {
			x = startX;
			y = startY;

			GlyphState = 'idle';
			pointerId = -1;
		}
	}

	let dropTarget = $state<HTMLDivElement>();
	let isOverTarget = $state(false);

	function updateTarget(pointerX: number, pointerY: number) {
		if (dropTarget) {
			const rect = dropTarget.getBoundingClientRect();

			isOverTarget =
				pointerX >= rect.left &&
				pointerX <= rect.right &&
				pointerY >= rect.top &&
				pointerY <= rect.bottom;
		}
	}
</script>

<div class="arena">
	<button
		type="button"
		class="glyph"
		class:dragging={GlyphState === 'dragging'}
		style:transform={`translate(${x}px, ${y}px)`}
		onpointerdown={startDrag}
		onpointermove={moveDrag}
		onpointerup={endDrag}
		onpointercancel={cancelDrag}
		onlostpointercapture={cancelDrag}
	>
		<span class="bg-gray-400 p-4">
			{GlyphState}
		</span>
	</button>

	<div bind:this={dropTarget} class="drop-target" class:highlighted={isOverTarget}>
		{isOverTarget ? 'Release here' : 'Word slot'}
	</div>
</div>

<style>
	.arena {
		position: relative;
		height: 100vh;
		border: 1px dashed #888;
		overflow: hidden;
	}

	.glyph {
		position: absolute;
		left: 204px;
		top: 24px;
		width: 80px;
		height: 110px;
		border: 2px solid #355c44;
		border-radius: 12px;
		background: #dcebdc;
		color: #183322;
		font-size: 10px;
		cursor: grab;
		user-select: none;
		touch-action: none;
		transition: transform 40ms ease-in-out;
	}

	.glyph.dragging {
		cursor: grabbing;
		background: #b8d8b8;
	}

	.drop-target {
		position: absolute;
		right: 24px;
		top: 180px;
		width: 140px;
		height: 120px;
		box-sizing: border-box;

		display: grid;
		place-items: center;

		border: 2px dashed #888;
		border-radius: 12px;
		background: #eeeeee;
		color: #333;

		transition:
			background-color 120ms,
			border-color 120ms;
	}

	.drop-target.highlighted {
		border-color: #287344;
		background: #c8e8d0;
	}

	/* Keep the dragged Glyph above the target. */
	.glyph {
		z-index: 1;
	}
</style>
