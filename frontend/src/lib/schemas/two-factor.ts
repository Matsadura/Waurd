import * as v from 'valibot';

export const twoFactorCodeSchema = v.object({
	code: v.pipe(
		v.string(),
		v.trim(),
		v.regex(/^\d{6}$/, 'Please enter a valid 6-digit code.')
	)
});