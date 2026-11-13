<script lang="ts">
	import { page } from '$app/state';
	import WaurdLogo from '#lib/components/WaurdLogo.svelte';
	import SearchBar from './SearchBar.svelte';

	type NavLink = {
		href: string;
		label: string;
		icon: string;
	};

	let {
		open = $bindable(false),
		navLinks
	}: {
		open?: boolean;
		navLinks: NavLink[];
	} = $props();

	function closeMenu() {
		open = false;
	}
</script>

<!-- Backdrop: clicking outside closes the drawer -->
{#if open}
	<button
		type="button"
		class="fixed inset-0 z-55 cursor-default bg-black/65
			backdrop-blur-[2px] md:hidden"
		tabindex="-1"
		aria-hidden="true"
		onclick={closeMenu}
	></button>
{/if}

<!-- Mobile off-canvas drawer -->
<nav
	id="mobile-navigation"
	aria-label="Mobile navigation"
	inert={!open}
	class={`fixed inset-y-0 left-0 z-60 flex w-[min(20rem,85vw)]
		flex-col border-r border-white/10 bg-[#17131d] text-text-primary
		shadow-2xl transition-transform duration-300 ease-out md:hidden
		${open ? 'translate-x-0' : '-translate-x-full'}`}
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
			onclick={closeMenu}
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
					onclick={closeMenu}
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
		<SearchBar mobile />
	</div>
</nav>

<style>
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
