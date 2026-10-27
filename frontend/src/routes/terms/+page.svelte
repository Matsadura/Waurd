<script lang="ts">
	const sections = [
		{ id: 'agreement', title: '1. Agreement to These Terms' },
		{ id: 'eligibility', title: '2. Eligibility and Accounts' },
		{ id: 'security', title: '3. Account Security' },
		{ id: 'fair-play', title: '4. Fair Play and Conduct' },
		{ id: 'content', title: '5. Usernames and Content' },
		{ id: 'game', title: '6. Game Availability and Changes' },
		{ id: 'ownership', title: '7. Intellectual Property' },
		{ id: 'termination', title: '8. Suspension and Termination' },
		{ id: 'disclaimer', title: '9. Disclaimers and Liability' },
		{ id: 'changes', title: '10. Changes to These Terms' },
		{ id: 'contact', title: '11. Contact' }
	];
</script>

<svelte:head>
	<title>Terms of Service</title>
	<meta
		name="description"
		content="Read the Terms of Service for Waurd, the player-versus-player word battle game."
	/>
</svelte:head>

<div
	class="min-h-dvh w-full min-w-0 overflow-x-clip bg-background
	       bg-[url('/images/background.png')] bg-cover bg-fixed bg-center
	       px-4 py-6 text-text-primary
	       sm:px-6 sm:py-10 lg:px-8 lg:py-12"
>
	<header
		class="mx-auto mb-8 flex w-full max-w-5xl flex-wrap items-center justify-between gap-4 sm:mb-12"
	>
		<a
			href="/login"
			class="font-['Henny_Penny'] text-3xl font-normal tracking-wide text-accent
			       [text-shadow:2px_3px_5px_rgba(115,20,20,0.8)]
			       sm:text-4xl lg:text-5xl"
		>
			Waurd
		</a>

		<a
			href="/register"
			class="rounded-lg border border-accent/60 px-4 py-2 text-sm text-white
			       transition hover:bg-accent/15 focus-visible:outline-2
			       focus-visible:outline-offset-4 focus-visible:outline-accent
			       sm:px-5 sm:py-2.5 sm:text-base"
		>
			Back to Register
		</a>
	</header>

	<main
		class="mx-auto w-full max-w-4xl rounded-2xl border border-white/10
	             bg-[#15121b]/95 p-5 shadow-2xl shadow-black/40
	             sm:p-8 md:p-10 lg:p-12"
	>
		<div class="mb-8 border-b border-white/10 pb-6 sm:mb-10 sm:pb-8">
			<p class="mb-3 text-sm font-bold tracking-[0.2em] text-accent uppercase sm:text-base">
				WAURD · LEGAL
			</p>

			<h1 class="text-3xl leading-tight font-bold text-white sm:text-4xl lg:text-5xl">
				Terms of Service
			</h1>

			<p class="mt-4 text-base leading-relaxed text-white/70 sm:text-lg">
				These terms explain the basic rules for using Waurd, creating an account, and playing with
				other people.
			</p>

			<p class="mt-4 text-sm text-white/50 sm:text-base">
				Draft for project review · October 27, 2026
			</p>
		</div>

		<nav
			aria-label="Table of contents"
			class="mb-10 rounded-xl border border-white/10 bg-black/20 p-4
			       sm:mb-12 sm:p-6"
		>
			<h2 class="mb-4 text-xl font-bold text-accent sm:text-2xl">Table of Contents</h2>

			<ol class="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2 sm:gap-y-3">
				{#each sections as section (section.id)}
					<li>
						<a
							href="#{section.id}"
							class="inline-block py-1 text-base text-white/80 underline-offset-4
							       transition hover:text-accent hover:underline
							       focus-visible:outline-2 focus-visible:outline-accent
							       sm:text-lg"
						>
							{section.title}
						</a>
					</li>
				{/each}
			</ol>
		</nav>

		<div class="space-y-9 sm:space-y-11">
			<section id="agreement" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">1. Agreement to These Terms</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Welcome to Waurd. These Terms of Service describe the rules that apply when you access or
					use the Waurd website and game. By using Waurd, you agree to follow these terms and any
					applicable laws. If you do not agree, please do not use the service.
				</p>
				<p class="mt-3 text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					These terms are an initial project draft and must be reviewed and finalized before they
					are relied upon as the terms of a publicly operated service.
				</p>
			</section>

			<section id="eligibility" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">2. Eligibility and Accounts</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Some Waurd features may require you to create an account. When registering, you should
					provide accurate information and keep it up to date. You may not create an account by
					impersonating another person or using information you are not authorized to use.
				</p>
				<p class="mt-3 text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Any minimum-age requirements and rules for users who need parental or guardian consent
					must be established before the service launches.
				</p>
			</section>

			<section id="security" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">3. Account Security</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					You are responsible for protecting your login credentials and for activities carried out
					through your account, subject to applicable law. Do not share your password or attempt to
					access another user's account without permission. If you suspect unauthorized access,
					contact the Waurd team through the contact method provided by the project.
				</p>
			</section>

			<section id="fair-play" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">4. Fair Play and Conduct</h2>
				<p class="mb-3 text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Waurd is designed to be a competitive game that players can enjoy together. While using
					the service, you agree not to:
				</p>
				<ul
					class="list-disc space-y-2 pl-6 text-base leading-7 text-white/80 sm:text-lg sm:leading-8"
				>
					<li>Cheat, exploit bugs, or manipulate matches or rankings.</li>
					<li>Use unauthorized bots, scripts, or tools to gain an unfair advantage.</li>
					<li>Harass, threaten, or deliberately abuse other players.</li>
					<li>Attempt to disrupt, damage, or gain unauthorized access to the service.</li>
					<li>Use Waurd for unlawful purposes or violate another person's rights.</li>
				</ul>
			</section>

			<section id="content" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">5. Usernames and Content</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					You are responsible for the usernames, messages, and other material you submit, where such
					features are available. Do not submit content that is unlawful, threatening, abusive,
					deceptive, or that infringes another person's rights. Usernames or content that violate
					the rules may be subject to moderation under policies established by the Waurd team.
				</p>
			</section>

			<section id="game" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">
					6. Game Availability and Changes
				</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Game features, matchmaking, rankings, and other functionality may change as Waurd
					develops. The service may occasionally be unavailable due to maintenance, technical
					issues, or circumstances outside the project team's control. We will aim to keep the game
					working reliably, but uninterrupted availability cannot be guaranteed.
				</p>
			</section>

			<section id="ownership" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">7. Intellectual Property</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Waurd's original name, branding, artwork, interface, and software may be protected by
					intellectual property laws. These terms do not transfer ownership of those materials to
					you. You may use the service for its intended purpose, but you may not copy, redistribute,
					or commercially exploit protected materials without appropriate permission.
				</p>
				<p class="mt-3 text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					This section does not claim ownership of third-party materials or user-created content
					that the project team does not own.
				</p>
			</section>

			<section id="termination" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">
					8. Suspension and Termination
				</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					If account moderation is implemented, accounts may be restricted or suspended for serious
					or repeated violations of these terms, abuse, cheating, or threats to the security of the
					service. Any enforcement process should be applied consistently and in accordance with
					applicable law. The final policy for appeals and account deletion remains to be defined.
				</p>
			</section>

			<section id="disclaimer" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">9. Disclaimers and Liability</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Waurd is a game project provided as it is currently developed. To the extent permitted by
					applicable law, the project team does not guarantee that every feature will always be
					available or error-free. Nothing in these terms excludes or limits any rights or liability
					that cannot legally be excluded or limited.
				</p>
				<p class="mt-3 text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					Any final limitation-of-liability provisions must be reviewed for the laws applicable to
					the service and its operator.
				</p>
			</section>

			<section id="changes" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">10. Changes to These Terms</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					These terms may be updated as Waurd's features and policies develop. When a finalized
					version is changed, its displayed revision date should be updated. Any notice or
					acceptance requirements will be handled in accordance with applicable law.
				</p>
			</section>

			<section id="contact" class="scroll-mt-8">
				<h2 class="mb-3 text-xl font-bold text-accent sm:text-2xl">11. Contact</h2>
				<p class="text-base leading-7 text-white/80 sm:text-lg sm:leading-8">
					If you have a question about these terms, use the official contact method provided by the
					Waurd project. Contact details will be added here once the project has established an
					appropriate support channel.
				</p>
			</section>
		</div>

		<footer class="mt-12 border-t border-white/10 pt-6 sm:mt-16 sm:pt-8">
			<a
				href="/register"
				class="inline-flex min-h-11 items-center justify-center rounded-lg
				       bg-accent-action px-5 py-2.5 text-base font-bold text-white
				       shadow-md shadow-black/30 transition hover:brightness-110
				       focus-visible:outline-2 focus-visible:outline-offset-4
				       focus-visible:outline-white sm:text-lg"
			>
				Back to Register
			</a>

			<p class="mt-5 text-sm leading-relaxed text-white/50 sm:text-base">
				Waurd · Terms of Service · Draft for review
			</p>
		</footer>
	</main>
</div>

<style>
	@font-face {
		font-family: 'Henny Penny';
		src: url('/fonts/HennyPenny-Regular.ttf') format('truetype');
		font-weight: 400;
		font-style: normal;
	}
</style>
