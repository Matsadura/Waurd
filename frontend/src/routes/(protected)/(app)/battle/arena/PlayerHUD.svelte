<script lang="ts">
	import type { Player } from '#lib/utils/Player.svelte.ts';

	let {
		player,
		side = 'right',
		isTurn = false
	}: {
		player: Player;
		side?: 'left' | 'right';
		isTurn?: boolean;
	} = $props();

	const mirrored = $derived(side === 'left');
</script>

<section
	class={[
		'flex max-w-xl min-w-0 flex-1 items-center gap-2 p-1.5 font-kreon text-arena-yallow-100 md:gap-3',
		mirrored && 'flex-row-reverse'
	]}
>
	<div class="flex shrink-0 cursor-pointer flex-col items-center">
		<a
			class="size-10 cursor-pointer overflow-hidden rounded-full border-2 border-arena-yallow-100 bg-black/40 shadow-lg ring-2 shadow-arena-yallow-100/30 ring-black/30 hover:border-green-600 hover:shadow-green-600 sm:size-12 md:size-14 lg:size-16 2xl:size-20"
			href="https://www.youtube.com/watch?v=xdovIDv6SHM"
			target="_blank"
		>
			{#if player.avatar}
				<img src={player.avatar} alt="" class="size-full object-cover" draggable="false" />
			{:else}
				<span class="grid size-full place-items-center text-lg md:text-2xl lg:text-3xl">
					{player.name.charAt(0)}
				</span>
			{/if}
		</a>
		<span
			class="relative -mt-2 rounded-full border border-card-skill bg-arena-yallow-100 px-1.5 py-px text-xs leading-tight font-bold text-card-skill lg:text-sm"
		>
			{player.label}
		</span>
	</div>

	<div class="flex min-w-0 flex-1 flex-col gap-1 lg:gap-1.5">
		<header class={['flex items-center justify-between gap-2', mirrored && 'flex-row-reverse']}>
			<h2
				class="truncate text-base leading-snug font-bold md:text-xl lg:text-2xl"
				class:turn-flash={isTurn}
			>
				{player.name}
			</h2>

			<!-- Clock -->
			<span
				class={[
					'flex items-center justify-center gap-1 rounded bg-arena-yallow-100 px-2 py-0.5 text-sm leading-none font-bold text-card-skill tabular-nums motion-reduce:animate-none md:w-28 md:px-2.5 md:py-2.5 md:text-xl lg:w-32 lg:text-2xl',
					isTurn && (player.timeLeft > 60 ? 'active-clock' : 'active-clock-danger')
				]}
			>
				<svg
					viewBox="0 0 24 24"
					class="hidden size-4 md:block lg:size-5"
					fill="none"
					stroke="currentColor"
					stroke-width="2.5"
					stroke-linecap="round"
					aria-hidden="true"
				>
					<circle cx="12" cy="12" r="9" />
					<path d="M12 7v5l3 2" />
				</svg>
				{player.timer}
			</span>
		</header>

		<div
			class="grid h-4 w-full grid-cols-1 overflow-hidden rounded border-2 border-arena-yallow-100/60 bg-black/50 shadow-inner shadow-green-900/90 md:h-5 lg:h-7"
			role="meter"
			aria-label="Health"
			aria-valuemin={0}
			aria-valuemax={player.maxHp}
			aria-valuenow={player.hp}
		>
			<!-- Lagging damage trail -->
			<div
				class={[
					'col-start-1 row-start-1 bg-rose-300 transition-all delay-300 duration-700 ease-out motion-reduce:transition-none',
					mirrored && 'justify-self-end'
				]}
				style:width="{player.healthBarPercentage}%"
			></div>

			<!-- Current health -->
			<div
				class={[
					'col-start-1 row-start-1 border-rose-500/60 bg-rose-700 bg-linear-to-b from-white/25 to-transparent transition-all duration-300 ease-out motion-reduce:transition-none',
					mirrored ? 'justify-self-end border-l-2' : 'border-r-2'
				]}
				style:width="{player.healthBarPercentage}%"
			></div>
			<!-- Ticks -->
			<div class="col-start-1 row-start-1 grid grid-cols-4 divide-x-2 divide-arena-yallow-100/20">
				<span></span><span></span><span></span><span></span>
			</div>
			<!-- HP text -->
			<span
				class={[
					'col-start-1 row-start-1 self-center px-1.5 text-xs font-bold whitespace-nowrap drop-shadow-md md:px-2 md:text-sm lg:text-base',
					mirrored && 'justify-self-end'
				]}
			>
				{player.hp} / {player.maxHp}
			</span>
		</div>

		<!-- Effects -->
		<ul
			class={[
				'flex flex-wrap items-center gap-1 text-xs font-bold md:gap-1.5 md:text-sm lg:text-base',
				mirrored && 'flex-row-reverse'
			]}
		>
			{#each player.effects as effect}
				<li
					class={[
						'flex items-center gap-1 rounded-md border border-arena-yallow-100/30 bg-black/30 px-1.5',
						mirrored && 'flex-row-reverse'
					]}
					aria-label="{effect.name} effect"
				>
					<span class="mt-1 text-xl text-rose-500">&#10084;</span>
					{effect.amount}
					{effect.name[0].toLocaleUpperCase() + effect.name.slice(1).toLocaleLowerCase()}
				</li>
			{/each}
		</ul>
	</div>
</section>

<style>
	.shake {
		animation: horizontal-shaking 300ms ease-in-out;
	}

	@keyframes horizontal-shaking {
		0% {
			transform: translateX(0);
		}
		25% {
			transform: translateX(5px);
		}
		50% {
			transform: translateX(-5px);
		}
		75% {
			transform: translateX(5px);
		}
		100% {
			transform: translateX(0);
		}
	}

	.turn-flash {
		outline-offset: 2px;
		animation: turn-flash 800ms steps(1, end) 1;
	}

	@keyframes turn-flash {
		0%,
		40%,
		80% {
			color: var(--color-arena-yallow-100);
		}
		20%,
		60%,
		100% {
			color: var(--color-green-700);
		}
	}
	.active-clock-danger {
		animation: turn-ring-danger 700ms cubic-bezier(0.9, 0, 0.1, 1) infinite alternate;
	}

	@keyframes turn-ring-danger {
		to {
			background-color: var(--color-red-800);
			color: var(--color-arena-yallow-100);
		}
	}

	.active-clock {
		animation: turn-ring 1s cubic-bezier(0.9, 0, 0.1, 1) infinite alternate;
	}

	@keyframes turn-ring {
		to {
			background-color: var(--color-card-skill);
			color: var(--color-arena-yallow-100);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.shake,
		.turn-flash,
		.active-clock {
			animation: none;
		}
	}
</style>
