import * as v from 'valibot';

export const registerSchema = v.pipe(
	v.object({
		username: v.pipe(
			v.string(),
			v.trim(),
			v.minLength(3, 'Username must be at least 3 characters.'),
			v.maxLength(32, 'Username must be at most 32 characters.')
		),
		email: v.pipe(v.string(), v.trim(), v.email('Please enter a valid email address.')),
		password: v.pipe(
			v.string(),
			v.minLength(8, 'Password must be at least 8 characters.'),
			v.maxLength(128, 'Password must be at most 128 characters.')
		),
		confirmPassword: v.string(),
		termsAccepted: v.boolean()
	}),
	v.forward(
		v.partialCheck(
			[['password'], ['confirmPassword']],
			(input) => input.password === input.confirmPassword,
			'Passwords do not match.'
		),
		['confirmPassword']
	),
	v.forward(
		v.partialCheck(
			[['termsAccepted']],
			(input) => input.termsAccepted,
			'You must accept our Terms of Service.'
		),
		['termsAccepted']
	)
);
