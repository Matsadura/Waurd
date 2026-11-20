<script lang="ts">
	let { won, reason, eloDelta }: { won: boolean; reason: string; eloDelta: number | null } =
		$props();
</script>

<div
	class="fixed inset-0 z-50 grid place-items-center bg-black/75 p-4"
	role="dialog"
	aria-modal="true"
	aria-labelledby="end-title"
>
	<div class="w-full max-w-md rounded-2xl border border-white/15 bg-[#17141d] p-6 text-center">
		<h2
			id="end-title"
			class={['font-henny-penny text-5xl', won ? 'text-accent-action' : 'text-accent-red']}
		>
			{won ? 'Victory' : 'Defeat'}
		</h2>
		<p class="mt-3 text-lg text-white/80">{reason}</p>
		{#if eloDelta !== null}
			<p class="mt-1 text-white/60">Rating {eloDelta >= 0 ? '+' : ''}{eloDelta}</p>
		{/if}
		<a
			href="/play"
			class="mt-6 inline-block rounded-lg bg-accent-action px-6 py-2.5 text-lg text-white hover:brightness-110"
		>
			Play again
		</a>
	</div>
</div>
