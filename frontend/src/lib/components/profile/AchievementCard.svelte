<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Meter from '#lib/components/ui/Meter.svelte';
	import type { Achievement } from '#lib/types/profile.ts';

	let { achievement }: { achievement: Achievement } = $props();

	const done = $derived(achievement.progress >= achievement.target);
</script>

<Frame variant="double-border" as="article" class="flex gap-4 px-4 py-4">
	<!-- No icon yet? The Avatar falls back to the first letter, swap in iconUrl when we have art. -->
	<Avatar
		name={achievement.name}
		src={achievement.iconUrl}
		alt=""
		class="size-14 text-2xl {done ? '' : 'opacity-50 grayscale'}"
	/>

	<div class="min-w-0 flex-1">
		<h3 class="font-display text-xl">{achievement.name}</h3>
		<p class="text-ash">{achievement.description}</p>

		{#if done}
			<p class="mt-2 text-base text-success-light italic">
				Achieved {achievement.unlockedAt} · +{achievement.xpReward} XP
			</p>
		{:else}
			<Meter
				value={achievement.progress}
				max={achievement.target}
				label="{achievement.name} progress"
				class="mt-3"
			/>
			<p class="mt-1 text-base text-ash">
				{achievement.progress} / {achievement.target} · +{achievement.xpReward} XP
			</p>
		{/if}

		{#if achievement.rewardPerk}
			<p class="mt-1 text-base text-warning-light">Reward: {achievement.rewardPerk}</p>
		{/if}
	</div>
</Frame>
