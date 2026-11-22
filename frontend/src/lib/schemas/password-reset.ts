import * as v from 'valibot';

export const forgotPasswordSchema = v.object({
	email: v.pipe(v.string(), v.trim(), v.email('Please enter a valid email address.'))
});

export const resetPasswordSchema = v.pipe(
	v.object({
		newPassword: v.pipe(
			v.string(),
			v.minLength(8, 'Password must be at least 8 characters.'),
			v.maxLength(128, 'Password must be at most 128 characters.')
		),
		confirmPassword: v.string()
	}),
	v.forward(
		v.partialCheck(
			[['newPassword'], ['confirmPassword']],
			(input) => input.newPassword === input.confirmPassword,
			'Passwords do not match.'
		),
		['confirmPassword']
	)
);
