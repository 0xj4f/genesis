// Stable codes from the API's SSO redirect, mapped to user-facing text.
export const SSO_ERRORS = {
  account_exists: 'An account with this email already exists. Sign in with your password, then link the provider from your profile.',
  already_linked: 'That provider account is already linked to a different user.',
  account_disabled: 'This account is deactivated.',
  provider_denied: 'Sign-in was cancelled at the provider.',
  provider_error: 'The provider could not complete sign-in. Please try again.',
  invalid_request: 'The sign-in link expired or was already used. Please try again.',
  sso_failed: 'Single sign-on failed. Please try again.',
};

export const SCOPE_DESCRIPTIONS = {
  openid: 'Confirm who you are',
  profile: 'Your name and profile picture',
  email: 'Your email address',
  offline_access: 'Stay signed in (refresh tokens)',
};
