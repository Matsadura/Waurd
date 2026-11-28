<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Meter from '#lib/components/ui/Meter.svelte';
	import type { Achievement } from '#lib/types/profile.ts';

	let { achievement }: { achievement: Achievement } = $props();

	const done = $derived(achievement.completed);
</script>

<Frame variant="double-border" as="article" class="flex h-full min-h-40 gap-4 px-4 py-4">
	{#if done}
		<span class="absolute inset-y-2 left-1 w-1 bg-warning-light/80" aria-hidden="true"></span>
	{/if}

	<Avatar
		name={achievement.name}
		src={achievement.iconUrl}
		alt=""
		class="size-14 text-2xl {done ? '' : 'opacity-50 grayscale'}"
	/>

	<div class="flex min-w-0 flex-1 flex-col">
		<div class="flex flex-wrap items-baseline justify-between gap-x-3">
			<h3 class="font-display text-xl">{achievement.name}</h3>

			<span
				class={done
					? 'text-xs font-bold tracking-wider text-warning-light uppercase'
					: 'text-xs tracking-wider text-ash/70 uppercase'}
			>
				{done ? '✓ Unlocked' : 'Locked'}
			</span>
		</div>

		<p class="text-ash">{achievement.description}</p>

		<div class="mt-auto pt-3">
			{#if done}
				<p class="text-base text-success-light italic">
					Achieved {achievement.unlockedAt} · +{achievement.xpReward} XP
				</p>
			{:else}
				<Meter
					value={achievement.progress}
					max={achievement.target}
					label="{achievement.name} progress"
				/>
				<p class="mt-1 text-base text-ash">
					{achievement.progress} / {achievement.target} · +{achievement.xpReward} XP
				</p>
			{/if}

			{#if achievement.rewardPerk}
				<p class="mt-1 text-base text-warning-light">
					Reward: {achievement.rewardPerk}
				</p>
			{/if}
		</div>
	</div>
</Frame>
