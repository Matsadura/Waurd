<script lang="ts">
	import { FEEL } from '#lib/configs/arenaFeel.ts';
	import horse from '#lib/assets/horse.png';

	let {
		letter = 'F*'
	}: {
		letter: string;
	} = $props();
</script>

<!-- Doesn't make any sense to use the tailwind crap here, 
     cause all the units are ralative to the container size 
	 something apperntly tailwnid never planed to support? 
	 look up maybe I am wrong? -->
<article class="card rounded" style:aspect-ratio={FEEL.glyphAspectRatio}>
	<div class="card__frame rounded">
		<header class="card__header">
			<div class="card__header-top">
				<span class="card__rank">{letter}</span>
				<span class="card__type">SKILL</span>
			</div>
			<img src={horse} alt="knight icon" class="card__icon" />
		</header>

		<main class="card__body">{letter}</main>

		<footer class="card__footer">
			<p class="card__description">Deal <b class="text-red-300">90</b> damage</p>
			<p class="card__modifier">
				The modifier slot description, and also this can grow up a little bit?
			</p>
		</footer>
	</div>
</article>

<style>
	.card {
		--card-bg: #063528;
		--card-text: #fff1c3;
		--card-subtext: #fee2e2;
		--card-border: #fff1c3;
		--card-border: #fff1c3;

		container-type: inline-size;
		width: 100%;
		padding: 0.4cqi;
		background-color: var(--card-bg);
		color: var(--card-text);
		font-family: 'Kreon', serif;
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
		margin-top: 1cqi;
		width: 16cqi;
	}

	.card__body {
		text-align: center;
		font-size: 50cqi;
		line-height: 1;
	}

	.card__footer {
		margin: 5cqi 0cqi;
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		line-height: 1.25;
	}

	.card__description {
		font-size: 9cqi;
		margin-bottom: 8cqi;
	}

	.card__modifier {
		margin-top: 2cqi;
		font-size: 8cqi;
		color: var(--card-subtext);
		margin-bottom: 6cqi;
	}
</style>
