<script lang="ts">
	import Row from '#lib/components/ui/Row.svelte';
	import type { Match, MatchResult } from '#lib/types/profile.ts';

	// Pass href once there is a page for a single duel, then the row becomes a link.
	let { match, href }: { match: Match; href?: string } = $props();

	const resultWord: Record<MatchResult, string> = {
		win: 'Victory',
		loss: 'Defeat',
		draw: 'Draw'
	};

	const resultColor: Record<MatchResult, string> = {
		win: 'text-warning-light',
		loss: 'text-danger-light',
		draw: 'text-ash'
	};
</script>

<Row
	{href}
	title={match.opponent}
	note={match.opponentElo === null ? undefined : String(match.opponentElo)}
	subtitle={`${match.mode} · ${match.turns === null ? 'Turns unavailable' : `${match.turns} turns`} · ${match.date}`}
>
	<span
		class={[
			'block text-lg group-hover:text-bone group-focus-visible:text-bone',
			resultColor[match.result]
		]}>{resultWord[match.result]}</span
	>
	{#if match.eloChange !== null}
		<span class="row-sub block text-base">
			{match.eloChange > 0 ? '+' : ''}{match.eloChange} elo
		</span>
	{/if}
</Row>
