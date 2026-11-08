<script>
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';
</script>

<div
	class="relative z-50 flex h-dvh flex-col items-center justify-center overflow-y-scroll bg-gray-950/80 p-4 px-4 pt-12 md:pb-16"
>
	<div class="flex flex-col gap-8 md:flex-row">
		<div class="w-80 shrink-0 shadow-lg shadow-yellow-200/10">
			<GlyphFace letter="%" />
		</div>
		<div class="mt-8 flex flex-col">
			{#each Array(3) as _}
				<div class="mb-8 font-kreon">
					<h1 class="text-3xl font-bold text-yellow-500 text-shadow-cyan-300 text-shadow-xs">
						Vulnerable
					</h1>
					<p class="text-gray-300">Receive 50% more damage from Attacks for X turns...</p>
				</div>
			{/each}
		</div>
	</div>
</div>
