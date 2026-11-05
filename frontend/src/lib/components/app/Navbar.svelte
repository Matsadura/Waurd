<script lang="ts">
	import { page } from '$app/state';
	import WaurdLogo from '#lib/components/WaurdLogo.svelte';

	const navLinks = [
		{ href: '/play', label: 'PLAY', icon: 'gamepad-2' },
		// { href: '/chat', label: 'CHAT', icon: 'user-round' },
		{ href: '/guide', label: 'GUIDE', icon: 'book-open' },
		{ href: '/leaderboard', label: 'LEADERBOARD', icon: 'trophy' }
	];

	let mobileMenuOpen = $state(false);
	let profileMenuOpen = $state(false);
	let profileControls: HTMLDivElement;
	let username = $state('PlayerName'); //

	function openMobileMenu() {
		profileMenuOpen = false;
		mobileMenuOpen = true;
	}

	function toggleProfileMenu() {
		mobileMenuOpen = false;
		profileMenuOpen = !profileMenuOpen;
	}

	function closeMenus() {
		mobileMenuOpen = false;
		profileMenuOpen = false;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			closeMenus();
		}
	}

	function handleDocumentClick(event: MouseEvent) {
		if (!profileMenuOpen) {
			return;
		}

		if (event.target instanceof Node && !profileControls.contains(event.target)) {
			profileMenuOpen = false;
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />
<svelte:document onclick={handleDocumentClick} />

<nav
	class="sticky top-0 z-50 w-full min-w-0 border-b border-white/10
         px-3 py-3 backdrop-blur-md sm:px-2"
	aria-label="Main navigation"
>
	<div class="flex min-w-0 items-center justify-between gap-3">
		<div class="flex min-w-0 shrink-0 items-center gap-3 lg:gap-6">
			<!-- Mobile hamburger -->
			<button
				type="button"
				class="flex size-10 shrink-0 items-center justify-center rounded-md
					text-text-primary transition-colors hover:bg-white/10 md:hidden"
				aria-label="Open navigation menu"
				aria-expanded={mobileMenuOpen}
				aria-controls="mobile-navigation"
				onclick={openMobileMenu}
			>
				<svg
					viewBox="0 0 24 24"
					class="size-6"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
				>
					<path d="M4 7h16M4 12h16M4 17h16" />
				</svg>
			</button>

			<!-- Shared logo -->
			<WaurdLogo href="/play" size="small" />

			<!-- Desktop navigation -->
			<div class="hidden shrink-0 items-center gap-3 md:flex lg:gap-6">
				{#each navLinks as link (link.href)}
					<a
						href={link.href}
						aria-current={page.url.pathname === link.href ? 'page' : undefined}
						class="desktop-nav-link relative py-2 text-lg text-text-primary
							transition-colors hover:text-accent lg:text-xl"
					>
						{link.label}
					</a>
				{/each}
			</div>
		</div>

		<div class="flex shrink-0 items-center gap-2">
			<!-- Desktop search -->
			<form
				role="search"
				class="group hidden w-40 min-w-0 shrink-0 items-center gap-2
					border-b border-white/20 py-2 transition-colors
					focus-within:border-accent md:flex lg:w-48"
				onsubmit={(event) => event.preventDefault()}
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
					aria-label="Search players"
					placeholder="Find an opponent..."
					class="w-full min-w-0 border-0 bg-transparent p-0
						text-base text-text-primary/90 placeholder:text-white/50
						focus:ring-0"
				/>
			</form>

			<!-- <form
				class="hidden w-44 min-w-0 shrink-0 items-center gap-2 rounded-lg
					border border-white/10 bg-white/5 px-3 py-2
					md:flex lg:w-52"
				role="search"
				onsubmit={(event) => event.preventDefault()}
			>
				<svg
					viewBox="0 0 24 24"
					class="size-5 shrink-0 text-white/60"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
				>
					<circle cx="11" cy="11" r="7" />
					<path d="m20 20-4-4" />
				</svg>
				<input
					type="search"
					aria-label="Search players"
					placeholder="Search players..."
					class="w-full min-w-0 border-0 bg-transparent p-0 text-sm
						text-text-primary placeholder:text-white/40 focus:ring-0"
				/>
			</form> -->

			<!-- Notification button -->
			<button
				type="button"
				aria-label="Notifications"
				class="relative flex size-9 shrink-0 items-center justify-center
					rounded-md text-text-primary/80 transition-colors
					hover:text-accent sm:size-10"
			>
				<svg
					viewBox="0 0 24 24"
					class="size-5"
					fill="none"
					stroke="currentColor"
					stroke-width="1.8"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
					<path d="M10 21h4" />
				</svg>
				<span
					class="absolute top-2 right-2 size-1.5 rounded-full
						bg-accent-red"
					aria-label="Unread notifications"
				></span>
			</button>

			<!-- Profile menu -->
			<div bind:this={profileControls} class="relative shrink-0">
				<button
					type="button"
					aria-label="Open profile menu"
					aria-expanded={profileMenuOpen}
					aria-haspopup="true"
					class="group flex items-center gap-2 rounded-md py-2
						text-text-primary/80 transition-colors hover:text-accent sm:gap-2"
					onclick={toggleProfileMenu}
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
							${profileMenuOpen ? 'rotate-180' : ''}`}
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

				{#if profileMenuOpen}
					<div
						class="absolute top-full right-0 z-70 mt-3 w-48
							rounded-lg border border-white/10
							bg-[#1b1721] p-2 shadow-xl"
					>
						<a
							href="/profile"
							class="block rounded-md px-3 py-2 text-sm
								hover:bg-accent"
							onclick={closeMenus}
						>
							Profile
						</a>

						<a
							href="/inbox"
							class="block rounded-md px-3 py-2 text-sm
								hover:bg-accent"
							onclick={closeMenus}
						>
							Inbox
						</a>

						<a
							href="/settings"
							class="block rounded-md px-3 py-2 text-sm
								hover:bg-accent"
							onclick={closeMenus}
						>
							Settings
						</a>

						<div class="my-1 border-t border-white/10"></div>

						<button
							type="button"
							class="w-full rounded-md px-3 py-2 text-left
								text-sm hover:bg-accent-red"
							onclick={closeMenus}
						>
							Log out
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
</nav>

<!-- Backdrop: clicking outside closes the drawer -->
{#if mobileMenuOpen}
	<button
		type="button"
		class="fixed inset-0 z-55 cursor-default bg-black/65
            backdrop-blur-[2px] md:hidden"
		aria-label="Close navigation menu"
		onclick={() => (mobileMenuOpen = false)}
	></button>
{/if}

<!-- Mobile off-canvas drawer -->
<aside
	id="mobile-navigation"
	aria-label="Mobile navigation"
	aria-hidden={!mobileMenuOpen}
	class={`fixed inset-y-0 left-0 z-60 flex w-[min(20rem,85vw)]
        flex-col border-r border-white/10 bg-[#17131d] text-text-primary
        shadow-2xl transition-transform duration-300 ease-out md:hidden
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}
>
	<!-- Drawer header -->
	<div
		class="flex min-h-16 shrink-0 items-center gap-3 border-b
        border-white/10 px-3 py-3"
	>
		<button
			type="button"
			class="flex size-10 shrink-0 items-center justify-center rounded-md
                hover:bg-white/10"
			aria-label="Close navigation menu"
			onclick={() => (mobileMenuOpen = false)}
		>
			<svg
				viewBox="0 0 24 24"
				class="size-6"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
			>
				<path d="M18 6 6 18M6 6l12 12" />
			</svg>
		</button>

		<WaurdLogo href="/play" size="small" />
	</div>

	<!-- Drawer links and search -->
	<div class="flex-1 overflow-y-auto p-3">
		<div class="flex flex-col gap-1">
			{#each navLinks as link (link.href)}
				<a
					href={link.href}
					aria-current={page.url.pathname === link.href ? 'page' : undefined}
					class="mobile-nav-link flex items-center gap-3 rounded-md px-4 py-4
                        text-base text-text-primary transition-colors
                        hover:bg-white/5 hover:text-accent"
					onclick={() => (mobileMenuOpen = false)}
				>
					{#if link.icon === 'gamepad-2'}
						<svg
							viewBox="0 0 24 24"
							class="size-5 shrink-0"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M6 12h4m-2-2v4m7-3h.01M18 10h.01" />
							<path
								d="M6.5 7h11a4 4 0 0 1 3.9 4.9l-1 4A2.5 2.5 0 0 1 16 17l-2-2H10l-2 2a2.5 2.5 0 0 1-4.4-1.1l-1-4A4 4 0 0 1 6.5 7Z"
							/>
						</svg>
						<!-- {:else if link.icon === 'user-round'}
						<svg
							viewBox="0 0 24 24"
							class="size-5 shrink-0"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<circle cx="12" cy="8" r="4" />
							<path d="M5 21v-2a7 7 0 0 1 14 0v2" />
						</svg> -->
					{:else if link.icon === 'book-open'}
						<svg
							viewBox="0 0 24 24"
							class="size-5 shrink-0"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M12 7v14m0-14C9 4 5 4 3 5v14c2-1 6-1 9 2m0-14c3-3 7-3 9-2v14c-2-1-6-1-9 2" />
						</svg>
					{:else}
						<svg
							viewBox="0 0 24 24"
							class="size-5 shrink-0"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M8 21h8m-4-4v4M7 4h10l2 4-7 4-7-4 2-4Z" />
							<path d="m5 12 2 5h10l2-5" />
						</svg>
					{/if}

					<span>{link.label}</span>
				</a>
			{/each}
		</div>

		<div class="my-4 border-t border-white/10"></div>

		<!-- <form
			role="search"
			class="flex items-center gap-3 rounded-lg border border-white/10
                bg-white/5 px-3 py-3"
			onsubmit={(event) => event.preventDefault()}
		>
			<svg
				viewBox="0 0 24 24"
				class="size-5 shrink-0 text-white/60"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
			>
				<circle cx="11" cy="11" r="7" />
				<path d="m20 20-4-4" />
			</svg>
			<input
				type="search"
				aria-label="Search players"
				placeholder="Search players..."
				class="w-full min-w-0 border-0 bg-transparent p-0 text-sm
                    text-text-primary placeholder:text-white/40 focus:ring-0"
			/>
		</form> -->

		<form
			role="search"
			class="group flex w-full items-center gap-3 border-b
				border-white/20 py-3 transition-colors
				focus-within:border-accent"
			onsubmit={(event) => event.preventDefault()}
		>
			<svg
				viewBox="0 0 24 24"
				class="size-5 shrink-0 text-white/50
					transition-colors group-focus-within:text-accent"
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
				aria-label="Search players"
				placeholder="Find an opponent..."
				class="w-full min-w-0 border-0 bg-transparent p-0
					text-base text-text-primary/90
					placeholder:text-white/50 focus:ring-0"
			/>
		</form>
	</div>
</aside>

<style>
	.desktop-nav-link[aria-current='page']::before {
		content: '';
		position: absolute;
		top: -0.75rem;
		left: 50%;
		transform: translateX(-50%);
		border-top: 0.5rem solid var(--color-accent-red);
		border-left: 0.4rem solid transparent;
		border-right: 0.4rem solid transparent;
	}

	.mobile-nav-link[aria-current='page'] {
		background: rgb(239 70 55 / 10%);
		color: var(--color-accent-red);
	}

	.mobile-nav-link[aria-current='page']::before {
		content: '';
		width: 0;
		height: 0;
		margin-left: -0.65rem;
		margin-right: -0.1rem;
		border-top: 0.35rem solid transparent;
		border-bottom: 0.35rem solid transparent;
		border-left: 0.4rem solid var(--color-accent-red);
	}
</style>
