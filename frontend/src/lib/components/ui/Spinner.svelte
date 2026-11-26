<script lang="ts">
	type Props = {
		size?: 'sm' | 'md' | 'lg';
		label?: string;
		class?: string;
		disabled?: boolean;
	};

	let { size = 'md', disabled = false, label = 'Loading', class: className = '' }: Props = $props();

	const sizes: Record<NonNullable<Props['size']>, string> = {
		sm: 'size-4 border-2',
		md: 'size-6 border-2',
		lg: 'size-9 border-4'
	};
</script>

<span
	role="status"
	aria-label={label}
	class={[
		'inline-block rounded-full border-current border-t-transparent',
		sizes[size],
		className,
		disabled ? 'opacity-10' : 'animate-spin'
	]}
></span>
