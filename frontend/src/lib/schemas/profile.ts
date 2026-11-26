import * as v from 'valibot';

export const profileSchema = v.object({
	username: v.pipe(
		v.string(),
		v.trim(),
		v.minLength(3, 'Username must be at least 3 characters.'),
		v.maxLength(32, 'Username must be at most 32 characters.')
	),
	email: v.pipe(v.string(), v.trim(), v.email('Please enter a valid email address.'))
});
