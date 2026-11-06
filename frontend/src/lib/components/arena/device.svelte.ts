import { MediaQuery } from 'svelte/reactivity';

const narrow = new MediaQuery('(max-width: 640px)', false);

export const device = {
	get isMobile() {
		return narrow.current;
	}
};
