export type EffectName = 'attack' | 'defense' | 'heal' | 'weak' | 'vulnerable';
export type Effect = { name: EffectName; amount: number };

export type PlayerType = {
	name: string;
	avatar?: string;
	maxHp: number;
	hp?: number;
	label: 'You' | 'Opponent';

	timeLeft?: number; // in seconds
	effects?: Effect[];
};

const pad = (n: number) => String(n).padStart(2, '0');

export class Player {
	name = $state('');
	avatar = $state<string | undefined>();
	hp = $state(0);
	maxHp = $state(0);
	timeLeft = $state(0);
	effects = $state<Effect[]>([]);
	label = $state<'You' | 'Opponent'>();

	healthBarPercentage = $derived(
		this.maxHp > 0 ? Math.max(0, Math.min(100, (this.hp / this.maxHp) * 100)) : 0
	);
	isDead = $derived(this.hp <= 0);

	timer = $derived(`${pad(Math.floor(this.timeLeft / 60))}:${pad(this.timeLeft % 60)}`);

	constructor(init: PlayerType) {
		this.name = init.name;
		this.avatar = init.avatar;
		this.maxHp = init.maxHp;
		this.hp = init.hp ?? init.maxHp;
		this.timeLeft = init.timeLeft ?? 0;
		this.effects = init.effects ?? [];
		this.label = init.label;
	}

	takeDamage(amount: number) {
		this.hp = Math.max(0, this.hp - amount);
	}

	heal(amount: number) {
		this.hp = Math.min(this.maxHp, this.hp + amount);
	}

	addEffect(name: EffectName, amount = 1) {
		const existing = this.effects.find((e) => e.name === name);
		if (existing) existing.amount += amount;
		else this.effects.push({ name, amount });
	}

	removeEffect(name: EffectName) {
		this.effects = this.effects.filter((e) => e.name !== name);
	}
}
