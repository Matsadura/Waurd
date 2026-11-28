<script lang="ts">
	import { FEEL } from '#lib/utils/arena.svelte.ts';
	import type { GlyphEffectType, ServerGlyph } from '#lib/utils/battleSocket.svelte.ts';

	type EffectConfig = {
		before: string;
		after: string;
		icon: string;
	};

	const EFFECT_CONFIG: Record<GlyphEffectType, EffectConfig> = {
		damage: {
			before: 'Deal ',
			after: ' damage.',
			icon: '⚔'
		},
		heal: {
			before: 'Heal ',
			after: ' HP.',
			icon: '✚'
		},
		defense: {
			before: 'Gain ',
			after: ' defense.',
			icon: '🛡'
		},
		vulnerable: {
			before: 'Apply ',
			after: ' Vulnerable.',
			icon: '✦'
		},
		weak: {
			before: 'Apply ',
			after: ' Weak.',
			icon: '✧'
		}
	};

	let { glyph }: { glyph: ServerGlyph } = $props();

	const effect = $derived(EFFECT_CONFIG[glyph.effect_type]);
</script>

<!-- Doesn't make any sense to use the tailwind crap here, 
     cause all the units are ralative to the container size 
	 something apperntly tailwnid never planed to support? 
	 look up maybe I am wrong? -->
<article class="card rounded" data-type={glyph.type} style:aspect-ratio={FEEL.glyphAspectRatio}>
	<div class="card__frame rounded">
		<header class="card__header">
			<div class="card__header-top">
				<span class="card__rank">{glyph.letter}</span>
				<span class="card__type">{glyph.type.toUpperCase()}</span>
			</div>
			<p class="card__icon">{effect.icon}</p>
		</header>

		<main class="card__body">{glyph.letter}</main>

		<footer class="card__footer">
			<p class="card__description">
				{effect.before}<b class="text-yellow-400">{glyph.effect_value}</b>{effect.after}
			</p>
		</footer>
	</div>
</article>

<style>
	.card {
		--card-bg: #063528;
		--card-outer-border: var(--color-green-800);
		--card-text: #fff1c3;
		--card-subtext: #fee2e2;
		--card-border: #fff1c3;

		container-type: inline-size;
		width: 100%;
		padding: 0.4cqi;
		background-color: var(--card-bg);
		color: var(--card-text);
		font-family: 'Kreon', serif;
		border: 1px solid var(--card-outer-border);
		user-select: none;
	}

	.card[data-type='power'] {
		--card-bg: #063528;
		--card-outer-border: var(--color-green-800);
	}

	.card[data-type='skill'] {
		--card-bg: #36070a;
		--card-outer-border: #8a2c21;
	}

	.card__frame {
		display: flex;
		height: 100%;
		flex-direction: column;
		justify-content: space-between;
		border: 2cqi solid var(--card-border);
		padding: 2.5cqi;
		box-shadow:
			rgba(212, 206, 152, 0.25) 0px 6px 12px -2px,
			rgba(194, 193, 128, 0.3) 0px 3px 7px -3px;
	}

	.card__header {
		margin-top: 2cqi;
	}

	.card__header-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-inline: 2cqi;
		line-height: 1;
	}

	.card__rank {
		font-size: 20cqi;
	}

	.card__type {
		font-size: 12cqi;
	}

	.card__icon {
		font-size: 20cqi;
		line-height: 0.9;
		text-align: start;
	}

	.card__body {
		text-align: center;
		font-size: 50cqi;
		line-height: 1;
	}

	.card__footer {
		margin: 5cqi 1cqi;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		line-height: 1.25;
		min-height: 50cqi;
	}

	.card__description {
		font-size: 10cqi;
		margin-bottom: 8cqi;
	}
</style>
