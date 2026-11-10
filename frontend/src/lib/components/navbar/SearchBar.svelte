<script lang="ts">
	let {
		mobile = false
	}: {
		mobile?: boolean;
	} = $props();

	function handleSearch(event: SubmitEvent) {
		event.preventDefault();

		// TODO: Implement player search when the backend API is available.
	}
</script>

<form
	role="search"
	class={`group flex min-w-0 items-center border-b border-white/20
		transition-colors focus-within:border-accent
		${mobile ? 'w-full gap-3 py-3' : 'w-40 shrink-0 gap-2 py-2 lg:w-48'}`}
	onsubmit={handleSearch}
>
	<svg
		viewBox="0 0 24 24"
		class="size-5 shrink-0 text-white/50 transition-colors
			group-focus-within:text-accent"
		fill="none"
		stroke="currentColor"
		stroke-width="1.7"
		stroke-linecap="round"
		aria-hidden="true"
	>
		<circle cx="10.5" cy="10.5" r="6.5" />
		<path d="m15.5 15.5 4 4" />
		<path d="M8 10.5h5" opacity=".45" />
	</svg>

	<input
		type="search"
		name="search"
		aria-label="Search players"
		placeholder="Find an opponent..."
		class="w-full min-w-0 border-0 bg-transparent p-0
			text-base text-text-primary/90
			placeholder:text-white/50 focus:ring-0"
	/>
</form>
