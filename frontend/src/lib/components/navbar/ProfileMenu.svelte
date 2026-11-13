<script lang="ts">
	let {
		open = $bindable(false),
		username,
		ontoggle
	}: {
		open?: boolean;
		username: string;
		ontoggle: () => void;
	} = $props();

	let profileControls: HTMLDivElement;

	function closeMenu() {
		open = false;
	}

	function handleDocumentClick(event: MouseEvent) {
		if (!open || !profileControls) {
			return;
		}

		if (event.target instanceof Node && !profileControls.contains(event.target)) {
			closeMenu();
		}
	}
</script>

<svelte:document onclick={handleDocumentClick} />

<div bind:this={profileControls} class="relative shrink-0">
	<button
		type="button"
		aria-label="Open profile menu"
		aria-expanded={open}
		class="group flex items-center gap-2 rounded-md py-2
			text-text-primary/80 transition-colors hover:text-accent sm:gap-2"
		onclick={ontoggle}
	>
		<!-- Username -->
		<span class="hidden max-w-32 truncate text-base sm:block">
			{username}
		</span>

		<!-- Avatar -->
		<span
			class="flex shrink-0 items-center justify-center
				rounded-full border-2"
		>
			<svg
				viewBox="0 0 24 26"
				class="size-5"
				fill="none"
				stroke="currentColor"
				stroke-width="1.8"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<circle cx="12" cy="8" r="4" />
				<path d="M5 21v-2a7 7 0 0 1 14 0v2" />
			</svg>
		</span>

		<!-- Dropdown arrow -->
		<svg
			viewBox="0 0 24 24"
			class={`size-4 shrink-0 transition-transform duration-200
				${open ? 'rotate-180' : ''}`}
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="m6 9 6 6 6-6" />
		</svg>
	</button>

	{#if open}
		<div
			class="absolute top-full right-0 z-70 mt-3 w-48
				rounded-lg border border-white/15
				bg-[#231d2b]/95 p-2 shadow-2xl backdrop-blur-xl"
		>
			<a
				href="/profile"
				class="block rounded-md px-3 py-2 text-sm hover:bg-accent"
				onclick={closeMenu}
			>
				Profile
			</a>

			<a
				href="/inbox"
				class="block rounded-md px-3 py-2 text-sm hover:bg-accent"
				onclick={closeMenu}
			>
				Inbox
			</a>

			<a
				href="/settings"
				class="block rounded-md px-3 py-2 text-sm hover:bg-accent"
				onclick={closeMenu}
			>
				Settings
			</a>

			<div class="my-1 border-t border-white/10"></div>

			<button
				type="button"
				class="w-full rounded-md px-3 py-2 text-left text-sm hover:bg-accent-red"
				onclick={closeMenu}
			>
				Log out
			</button>
			<!-- TODO: Connect logout to the backend authentication endpoint -->
		</div>
	{/if}
</div>
