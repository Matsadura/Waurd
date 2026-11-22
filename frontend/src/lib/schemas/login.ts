import * as v from 'valibot';

export const loginSchema = v.object({
	email: v.pipe(v.string(), v.trim(), v.email('Please enter a valid email address.')),
	password: v.pipe(
		v.string(),
		v.minLength(8, 'Password must be at least 8 characters.'),
		v.maxLength(128, 'Password must be at most 128 characters.')
	)
});
