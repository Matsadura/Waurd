<script lang="ts">
	import { page } from '$app/state';
	import WaurdLogo from '#lib/components/WaurdLogo.svelte';
	import SearchBar from './SearchBar.svelte';
	import ProfileMenu from './ProfileMenu.svelte';
	import MobileNav from './MobileNav.svelte';

	const navLinks = [
		{ href: '/play', label: 'PLAY', icon: 'gamepad-2' },
		{ href: '/guide', label: 'GUIDE', icon: 'book-open' },
		{ href: '/leaderboard', label: 'LEADERBOARD', icon: 'trophy' }
	];

	let mobileMenuOpen = $state(false);
	let profileMenuOpen = $state(false);
	const username = 'PlayerName'; // TODO: Replace with authenticated user data.

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
</script>

<svelte:window onkeydown={handleKeydown} />

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
			<div class="hidden md:block">
				<SearchBar />
			</div>

			<!-- Notification button -->
			<!-- TODO: Connect notifications and unread status to backend data -->
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

			<ProfileMenu bind:open={profileMenuOpen} {username} ontoggle={toggleProfileMenu} />
		</div>
	</div>
</nav>

<MobileNav bind:open={mobileMenuOpen} {navLinks} />

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
</style>
