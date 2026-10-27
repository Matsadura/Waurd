<script lang="ts">
	import { page } from '$app/state';

	let { children } = $props();

	const tabs = [
		{ href: '/login', label: 'LOGIN' },
		{ href: '/register', label: 'REGISTER' },
		{ href: '/reset-password', label: 'RESET PASSWORD' }
	];
</script>

<svelte:head>
	<link
		rel="preload"
		href="/fonts/HennyPenny-Regular.ttf"
		as="font"
		type="font/ttf"
		crossorigin="anonymous"
	/>

	<link
		rel="preload"
		href="/fonts/Rajdhani-Bold.ttf"
		as="font"
		type="font/ttf"
		crossorigin="anonymous"
	/>
</svelte:head>

<div
	class="auth-page relative flex min-h-dvh w-full min-w-0 flex-col items-center overflow-x-clip bg-background
		bg-[url('/images/background.png')] bg-cover bg-center bg-no-repeat
		px-4 py-3 font-rajdhani font-bold text-text-primary sm:px-6 sm:py-6 lg:py-8 [@media_(min-width:640px)_and_(max-height:950px)]:py-2"
>
	<header class="auth-header mt-[clamp(0.5rem,3vh,3rem)] mb-3 sm:mb-5">
		<a
			href="/login"
			class="auth-logo font-henny-penny text-[clamp(2.5rem,min(12vw+2.5rem,20vh),11.875rem)] font-normal tracking-[2px] text-accent no-underline [text-shadow:5px_5px_8px_rgba(115,20,20,0.8),10px_7px_16px_rgba(100,15,15,0.55)]"
		>
			Waurd
		</a>
	</header>

	<div class="auth-column @container w-full max-w-2xl">
		<nav
			class="auth-tabs mb-5 flex flex-wrap justify-center gap-2 text-[clamp(0.9rem,calc(100cqw/23),1.5rem)] sm:mb-7 sm:gap-3"
		>
			{#each tabs as tab (tab.href)}
				<a
					href={tab.href}
					class="relative flex min-h-10 min-w-0 grow items-center justify-center
							rounded-md bg-accent-red
							px-[1.1em] py-[0.17em]
							text-center leading-[1.33] whitespace-nowrap
							text-white no-underline
							shadow-[0_0.42em_0.5em_rgba(0,0,0,0.45)]"
					aria-current={page.url.pathname === tab.href ? 'page' : undefined}
				>
					{tab.label}
				</a>
			{/each}
		</nav>

		<main class="mx-auto w-[max(65%,min(88%,20rem))]">
			{@render children()}
		</main>
	</div>
</div>

<style>
	@font-face {
		font-family: 'Henny Penny';
		src: url('/fonts/HennyPenny-Regular.ttf') format('truetype');
		font-weight: 400;
		font-style: normal;
	}

	@font-face {
		font-family: 'Rajdhani';
		src: url('/fonts/Rajdhani-Bold.ttf') format('truetype');
		font-weight: 700;
		font-style: normal;
	}

	/* The small triangle above the active tab (sized in em, so it scales with the tab text) */
	.auth-tabs a[aria-current='page']::before {
		content: '';
		position: absolute;
		left: 50%;
		top: -0.62em;
		transform: translateX(-50%);
		border-left: 0.42em solid transparent;
		border-right: 0.42em solid transparent;
		border-top: 0.62em solid var(--color-accent-red);
	}

	@media (min-width: 640px) and (max-height: 950px) {
		.auth-page {
			padding-top: 0.5rem;
			padding-bottom: 0.5rem;
		}

		.auth-header {
			margin-top: 0.5rem;
			margin-bottom: 0.5rem;
		}

		.auth-logo {
			font-size: clamp(3rem, 12vh, 6rem);
		}

		.auth-tabs {
			margin-bottom: 1rem;
		}
	}
</style>
